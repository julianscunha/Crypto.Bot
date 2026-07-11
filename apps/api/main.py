# -*- coding: utf-8 -*-

from datetime import (
    datetime
)

import sys

from pathlib import Path

from typing import (
    List
)

from fastapi import (
    Depends,
    FastAPI,
    Header,
    HTTPException,
    Request
)

from fastapi.middleware.cors import (
    CORSMiddleware
)

from fastapi.responses import (
    JSONResponse
)

from slowapi import (
    Limiter,
    _rate_limit_exceeded_handler
)

from slowapi.errors import (
    RateLimitExceeded
)

from slowapi.util import (
    get_remote_address
)

from core.config.settings import (
    settings
)

from core.utils.console_logger import (
    log
)

from core.config import (
    settings_repository
)

from core.state.market_state import (
    market_state,
    MarketState
)

from data.storage.repositories.runtime_state_repository import (
    runtime_state_repository
)

from core.services.trade_metrics_service import (
    trade_metrics_service
)

from core.services.risk_protection_service import (
    risk_protection_service
)

from core.config.trading_config import (
    TRADING_CONFIG
)

from data.storage.repositories.portfolio_repository import (
    portfolio_repository
)

from data.storage.repositories.trades_repository import (
    trades_repository
)

from core.services.process_manager_service import (
    restart_runner,
    stop_runner,
    start_runner,
    ProcessManagerError
)

from apps.api.schemas.metrics_schema import (
    MetricsResponse
)

from apps.api.schemas.advanced_metrics_schema import (
    AdvancedMetricsResponse
)

from apps.api.schemas.risk_schema import (
    RiskStatusResponse
)

from apps.api.schemas.portfolio_schema import (
    PortfolioResponse
)

from apps.api.schemas.trade_schema import (
    TradeResponse
)

from apps.api.schemas.settings_schema import (

    SettingsResponse,

    SettingsUpdateRequest
)

from apps.api.schemas.dashboard_schema import (

    DashboardResponse,

    RuntimeResponse
)

from data.storage.database import (
    init_db
)

# =====================================================
# API
# =====================================================

app = FastAPI(

    title="Crypto.Bot API",

    version="2.1.0"
)

# =====================================================
# RATE LIMITING
# =====================================================
#
# Applied only to the sensitive/mutating endpoints (settings, runner
# start/stop) -- see the `dependencies=[Depends(rate_limit)]`
# argument on each of those routes below. Read-only endpoints
# (dashboard, metrics, etc.) are polled frequently by the frontend
# and are not a meaningful attack surface on their own.

limiter = Limiter(
    key_func=get_remote_address
)

app.state.limiter = limiter

app.add_exception_handler(
    RateLimitExceeded,
    _rate_limit_exceeded_handler
)

SENSITIVE_ENDPOINT_RATE_LIMIT = settings.API_RATE_LIMIT

# =====================================================
# API TOKEN AUTH
# =====================================================
#
# Simple shared-secret auth via the X-API-Token header, applied to
# the same sensitive endpoints as the rate limiter above (PUT
# /settings, POST /runner/start, POST /runner/stop). API_ACCESS_TOKEN
# empty/unset (the default, matching this API's original
# localhost-only design) disables auth entirely -- see the startup
# warning below for the case where that's actually risky.

async def require_api_token(
    x_api_token: str | None = Header(default=None)
):

    token = settings.API_ACCESS_TOKEN

    if not token:
        return

    if x_api_token != token:

        raise HTTPException(
            status_code=401,
            detail="Token de API inválido ou ausente."
        )


@app.on_event("startup")
async def _startup():

    # A API agora pode subir antes do Runner (ou sem ele, quando o
    # usuário inicia o bot manualmente pela interface web). init_db()
    # é idempotente -- cria as tabelas se não existirem, não faz
    # nada se já existirem.
    init_db()

    is_localhost_only = settings.API_HOST in (
        "127.0.0.1",
        "localhost"
    )

    if not is_localhost_only and not settings.API_ACCESS_TOKEN:

        log(
            "SYSTEM",
            (
                f"API_HOST={settings.API_HOST} não é localhost e "
                "API_ACCESS_TOKEN não está configurado -- os "
                "endpoints de settings/runner ficam acessíveis sem "
                "autenticação para qualquer host que alcance esta "
                "porta. Configure API_ACCESS_TOKEN no .env antes de "
                "expor esta API além de localhost."
            ),
            "WARNING"
        )


# =====================================================
# UNHANDLED EXCEPTIONS
# =====================================================
#
# Without this, an unhandled exception inside a route handler still
# returns a 500 (FastAPI's default), but as an opaque, unlogged
# response -- nothing in logs/errors.log ties it back to what
# actually failed. This mirrors the EventBus's own per-subscriber
# isolation (core/bus/event_bus.py) at the API boundary: one route
# failing loudly must never look identical to a silent crash.

@app.exception_handler(Exception)
async def unhandled_exception_handler(
    request: Request,
    exc: Exception
):

    log(
        "SYSTEM",
        (
            f"Erro não tratado em {request.method} "
            f"{request.url.path}: {exc}"
        ),
        "CRITICAL"
    )

    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )


# =====================================================
# CORS
# =====================================================
#
# The dashboard frontend runs on a different origin than the API, so
# the browser needs CORS headers to be allowed to call it. Defaults
# to the Vite dev server's two localhost variants
# (settings.CORS_ALLOWED_ORIGINS) -- override via CORS_ALLOWED_ORIGINS
# in .env for other setups (e.g. the Docker-built frontend served by
# nginx on a different origin, see docker-compose.yml).
#
# allow_credentials is deliberately False: auth here is a custom
# X-API-Token header (see require_api_token above), never cookies --
# frontend/src/api/client.js's fetch() calls never set
# `credentials: "include"`. Turning this on would do nothing for this
# app's actual auth flow while widening the blast radius of a
# misconfigured CORS_ALLOWED_ORIGINS (e.g. an operator accidentally
# trusting an untrusted origin) to include cookie/credentialed
# requests that were never needed in the first place.

app.add_middleware(

    CORSMiddleware,

    allow_origins=settings.CORS_ALLOWED_ORIGINS,

    allow_credentials=False,

    allow_methods=["*"],

    allow_headers=["*"]
)

# =====================================================
# CONSTANTS
# =====================================================

DEFAULT_USER_ID = 0

RECENT_CLOSED_TRADES_LIMIT = 5

# =====================================================
# HELPERS
# =====================================================

def build_empty_portfolio_response():

    return PortfolioResponse(

        balance=0.0,

        equity=0.0,

        realized_pnl=0.0,

        unrealized_pnl=0.0,

        total_pnl=0.0,

        open_positions=0,

        closed_positions=0,

        exposure=0.0,

        drawdown=0.0,

        created_at=datetime.utcnow()
    )


def build_open_trade_response(
    trade
):

    return TradeResponse(

        id=trade.id,

        symbol=trade.symbol,

        action=trade.action,

        entry_price=trade.entry_price,

        current_price=trade.current_price,

        quantity=trade.quantity,

        pnl=trade.pnl,

        unrealized_pnl=trade.unrealized_pnl,

        status=trade.status
    )


def build_closed_trade_response(
    trade
):

    return TradeResponse(

        id=trade.id,

        symbol=trade.symbol,

        action=trade.action,

        entry_price=trade.entry_price,

        current_price=trade.current_price,

        quantity=trade.quantity,

        pnl=trade.pnl,

        realized_pnl=trade.realized_pnl,

        exit_reason=trade.exit_reason,

        status=trade.status,

        created_at=trade.created_at,

        closed_at=trade.closed_at
    )


def build_portfolio_response(
    snapshot
):

    if not snapshot:

        return build_empty_portfolio_response()

    return PortfolioResponse(

        balance=snapshot.balance,

        equity=snapshot.equity,

        realized_pnl=snapshot.realized_pnl,

        unrealized_pnl=snapshot.unrealized_pnl,

        total_pnl=snapshot.total_pnl,

        open_positions=snapshot.open_positions,

        closed_positions=snapshot.closed_positions,

        exposure=snapshot.exposure,

        drawdown=snapshot.drawdown,

        created_at=snapshot.created_at
    )


def build_runtime_response():

    # =====================================================
    # CROSS-PROCESS STATE
    # =====================================================
    #
    # apps.trader.runner runs as a separate OS process from this
    # API under Full Stack (see scripts/bootstrap/launcher.py), so
    # market_state here -- an in-memory singleton -- never sees the
    # Runner's actual writes (websocket_connected, active_symbols,
    # signal counters). Read the Runner's periodically-flushed state
    # from the database instead. Fall back to this process's own
    # (always-zeroed) MarketState only if the Runner has never
    # flushed at all, e.g. the API was started standalone.

    persisted_state = (
        runtime_state_repository.get()
    )

    if persisted_state is not None:

        runtime_snapshot = (
            MarketState
            .from_persisted(persisted_state)
            .snapshot()
        )

    else:

        runtime_snapshot = (
            market_state.snapshot()
        )

    return RuntimeResponse(

        # =================================================
        # CONNECTION
        # =================================================

        websocket_connected=runtime_snapshot[
            "websocket_connected"
        ],

        # =================================================
        # MARKET INGESTION
        # =================================================

        total_messages=runtime_snapshot[
            "total_market_messages"
        ],

        active_symbols=runtime_snapshot[
            "active_symbols"
        ],

        # =================================================
        # ANALYSIS PIPELINE
        # =================================================

        total_analysis_requests=runtime_snapshot[
            "total_analysis_requests"
        ],

        total_generated_signals=runtime_snapshot[
            "total_generated_signals"
        ],

        total_approved_signals=runtime_snapshot[
            "total_approved_signals"
        ],

        total_rejected_signals=runtime_snapshot[
            "total_rejected_signals"
        ],

        # =================================================
        # EXECUTION PIPELINE
        # =================================================

        total_executed_orders=runtime_snapshot[
            "total_executed_orders"
        ],

        total_closed_positions=runtime_snapshot[
            "total_closed_positions"
        ],

        # =================================================
        # TELEMETRY
        # =================================================

        blocked_signal_reasons=runtime_snapshot[
            "blocked_signal_reasons"
        ],

        execution_reasons=runtime_snapshot[
            "execution_reasons"
        ],

        # =================================================
        # METRICS
        # =================================================

        signal_generation_ratio=runtime_snapshot[
            "signal_generation_ratio"
        ],

        signal_approval_ratio=runtime_snapshot[
            "signal_approval_ratio"
        ],

        execution_ratio=runtime_snapshot[
            "execution_ratio"
        ],

        uptime_seconds=runtime_snapshot[
            "uptime_seconds"
        ]
    )

# =====================================================
# ROOT
# =====================================================

@app.get("/")
async def root():

    return {

        "name": "Crypto.Bot",

        "status": "running",

        "mode": settings.MODE,

        "version": "2.1.0"
    }

# =====================================================
# HEALTH
# =====================================================

@app.get("/health")
async def health():

    runtime_response = (
        build_runtime_response()
    )

    _s = settings_repository.get_settings()
    _mode = _s.get("mode", settings.MODE)
    _testnet = _s.get("binance_testnet", True)

    return {

        "status": "ok",

        "mode": _mode,

        "testnet": _testnet,

        "timestamp": datetime.utcnow(),

        "websocket_connected":
            runtime_response.websocket_connected,

        "uptime_seconds":
            runtime_response.uptime_seconds,

        # used by the frontend to calculate round-trip ping
        "server_time_ms": int(
            datetime.utcnow().timestamp() * 1000
        )
    }

# =====================================================
# RUNNER CONTROL (play / stop)
# =====================================================

@app.get("/runner/status")
async def runner_status():

    from core.utils.runner_pid import read_runner_pid
    from core.services.process_manager_service import _is_process_alive

    pid = read_runner_pid()

    running = (
        pid is not None
        and _is_process_alive(pid)
    )

    return {
        "running": running,
        "pid": pid if running else None
    }


@app.post(
    "/runner/stop",
    dependencies=[Depends(require_api_token)]
)
@limiter.limit(SENSITIVE_ENDPOINT_RATE_LIMIT)
async def runner_stop(request: Request):

    open_trades = trades_repository.get_open_trades(
        user_id=DEFAULT_USER_ID
    )

    if open_trades:

        raise HTTPException(
            status_code=409,
            detail=(
                f"Não é possível parar o bot com {len(open_trades)} "
                "posição(ões) aberta(s). Feche as posições primeiro."
            )
        )

    try:

        stop_runner()

    except ProcessManagerError as error:

        raise HTTPException(
            status_code=500,
            detail=f"Falha ao parar o bot: {error}"
        )

    return {"stopped": True}


@app.post(
    "/runner/start",
    dependencies=[Depends(require_api_token)]
)
@limiter.limit(SENSITIVE_ENDPOINT_RATE_LIMIT)
async def runner_start(request: Request):

    from core.utils.runner_pid import read_runner_pid
    from core.services.process_manager_service import _is_process_alive

    if _current_job["status"] == "running":
        raise HTTPException(
            status_code=409,
            detail="Aguarde o optimizer/backtest terminar antes de iniciar o bot."
        )

    pid = read_runner_pid()

    if pid is not None and _is_process_alive(pid):

        raise HTTPException(
            status_code=409,
            detail="O bot já está em execução."
        )

    balance_report = await build_startup_balance_report()
    if not balance_report["allowed"]:
        raise HTTPException(
            status_code=409,
            detail=balance_report["reason"] or "Saldo insuficiente para iniciar o bot."
        )

    try:

        process = start_runner()

    except Exception as error:

        raise HTTPException(
            status_code=500,
            detail=f"Falha ao iniciar o bot: {error}"
        )

    return {"started": True, "pid": process.pid}


@app.get("/runner/start-check")
async def runner_start_check():
    return await build_startup_balance_report()


# =====================================================
# OPTIMIZER & BACKTEST JOBS
# =====================================================
#
# Ambos rodam como subprocess separado para não bloquear a API.
# O estado do job fica em memória (_current_job) — simples e
# suficiente, já que só um job roda por vez.

import subprocess as _subprocess
import threading as _threading
import json as _json
import time as _time

from core.services.job_estimation_service import (
    estimate_job_duration_seconds,
    build_job_profile,
    get_system_profile,
    parse_days_from_extra_args,
)
from core.services.startup_balance_service import (
    build_startup_balance_report
)

_job_lock = _threading.Lock()

_current_job = {
    "type": None,
    "status": "idle",
    "started_at": None,
    "finished_at": None,
    "result": None,
    "error": None,
}

PROJECT_ROOT_STR = str(
    Path(__file__).resolve().parents[2]
)

_HISTORY_FILE = (
    Path(__file__).resolve().parents[2]
    / "backtest" / "reports" / "jobs_history.json"
)

MAX_HISTORY = 5


def _live_job_settings() -> tuple[list[str], str, float]:
    """
    core.config.settings.settings is a singleton computed once at
    process import -- SYMBOLS/KLINE_INTERVAL/MINIMUM_RISK_REWARD_RATIO
    stay stale in the running API process even after PUT /settings
    writes new values to .env (only a process restart reloads them).
    Job estimation/timeout must reflect what the user just saved, so
    read the same live .env source build_startup_balance_report()
    already uses instead of the stale static singleton.
    """

    live = settings_repository.get_settings()

    symbols = [
        symbol.strip().upper()
        for symbol in str(live.get("symbols", "")).split(",")
        if symbol.strip()
    ] or settings.SYMBOLS

    return (
        symbols,
        live.get("kline_interval", settings.KLINE_INTERVAL),
        float(live.get("minimum_risk_reward_ratio", settings.MINIMUM_RISK_REWARD_RATIO)),
    )


# =====================================================
# JOB TIMEOUT
# =====================================================
#
# subprocess.run's timeout used to be a flat 3600s regardless of
# workload -- an optimizer run over 90 days x 4 symbols has ~4x the
# work_units of the 90d x 1-symbol case the flat value was tuned
# against, so it got killed mid-run with a bare "timed out" error
# and no partial result. Reuse the same estimator that already
# powers the /jobs/estimate UI, with a wide safety margin (real
# runs vary a lot with market data size and machine load) and a
# floor/ceiling so a bad estimate can't produce an unreasonably
# short or effectively infinite timeout.
JOB_TIMEOUT_SAFETY_FACTOR = 3
JOB_TIMEOUT_FLOOR_SECONDS = 3600
JOB_TIMEOUT_CEILING_SECONDS = 6 * 3600


def _compute_job_timeout_seconds(job_type: str, days: int) -> int:
    try:
        symbols, interval, minimum_rr = _live_job_settings()
        estimate = estimate_job_duration_seconds(
            job_type=job_type,
            days=days,
            symbols=symbols,
            interval=interval,
            minimum_rr=minimum_rr,
            history=_load_history(),
        )
        timeout = estimate["estimate_seconds"] * JOB_TIMEOUT_SAFETY_FACTOR
    except Exception:
        timeout = JOB_TIMEOUT_FLOOR_SECONDS

    return min(
        max(timeout, JOB_TIMEOUT_FLOOR_SECONDS),
        JOB_TIMEOUT_CEILING_SECONDS,
    )


def _load_history() -> list:
    try:
        if _HISTORY_FILE.exists():
            return _json.loads(_HISTORY_FILE.read_text(encoding="utf-8"))
    except Exception:
        pass
    return []


def _save_history(entry: dict):
    history = _load_history()
    history.insert(0, entry)
    history = history[:MAX_HISTORY]
    try:
        _HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
        _HISTORY_FILE.write_text(
            _json.dumps(history, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
    except Exception:
        pass


def _build_history_workload(job_type: str, extra_args: list | None = None) -> dict:
    days = parse_days_from_extra_args(extra_args) if job_type == "optimizer" else 90
    symbols, interval, minimum_rr = _live_job_settings()

    return build_job_profile(
        job_type=job_type,
        days=days,
        symbols=symbols,
        interval=interval,
        minimum_rr=minimum_rr,
    )


def _run_job_subprocess(job_type: str, module: str, extra_args: list = None):

    global _current_job

    with _job_lock:
        _current_job = {
            "type": job_type,
            "status": "running",
            "started_at": _time.time(),
            "finished_at": None,
            "result": None,
            "error": None,
        }

    try:
        _run_job_subprocess_inner(job_type, module, extra_args)
    except Exception as exc:
        with _job_lock:
            if _current_job["status"] == "running":
                _current_job["status"] = "error"
                _current_job["finished_at"] = _time.time()
                _current_job["error"] = f"Erro inesperado: {exc}"


def _run_job_subprocess_inner(job_type: str, module: str, extra_args: list = None):

    workload = None
    hardware = None

    try:

        cmd = [sys.executable, "-m", module] + (extra_args or [])
        workload = _build_history_workload(job_type, extra_args)
        hardware = get_system_profile()

        progress_file = (
            Path(PROJECT_ROOT_STR) / "backtest" / "reports" / "progress.json"
        )

        try:
            progress_file.unlink(missing_ok=True)
        except Exception:
            pass

        import os as _os
        _env = _os.environ.copy()
        _env["PYTHONPATH"] = PROJECT_ROOT_STR

        job_timeout = _compute_job_timeout_seconds(
            job_type,
            workload.get("days", 90),
        )

        proc = _subprocess.run(
            cmd,
            cwd=PROJECT_ROOT_STR,
            capture_output=True,
            text=True,
            timeout=job_timeout,
            env=_env,
        )

        if proc.returncode != 0:
            stderr_tail = (proc.stderr or "").strip()[-1000:]
            raise RuntimeError(
                f"returncode={proc.returncode} | {stderr_tail or 'sem stderr'}"
            )

        # Ler o report JSON gerado pelo processo
        if job_type == "optimizer":
            report_path = Path(PROJECT_ROOT_STR) / "backtest" / "reports" / "optimizer_report.json"
        else:
            report_path = Path(PROJECT_ROOT_STR) / "backtest" / "reports" / "report.json"

        result = None
        if report_path.exists():
            with open(report_path, encoding="utf-8") as f:
                result = _json.load(f)

        with _job_lock:
            _current_job["status"] = "done"
            _current_job["finished_at"] = _time.time()
            _current_job["result"] = result

        elapsed = round(_time.time() - _current_job["started_at"])
        _save_history({
            "type": job_type,
            "status": "done",
            "started_at": _current_job["started_at"],
            "finished_at": _current_job["finished_at"],
            "elapsed_seconds": elapsed,
            "extra_args": extra_args or [],
            "workload": workload,
            "hardware": hardware,
            "result_summary": _extract_summary(result, job_type),
        })

    except Exception as exc:

        with _job_lock:
            _current_job["status"] = "error"
            _current_job["finished_at"] = _time.time()
            _current_job["error"] = str(exc)

        _save_history({
            "type": job_type,
            "status": "error",
            "started_at": _current_job["started_at"],
            "finished_at": _current_job["finished_at"],
            "elapsed_seconds": round(_time.time() - (_current_job["started_at"] or _time.time())),
            "extra_args": extra_args or [],
            "workload": workload,
            "hardware": hardware,
            "error": str(exc)[:200],
        })

    finally:

        try:
            progress_file = (
                Path(PROJECT_ROOT_STR) / "backtest" / "reports" / "progress.json"
            )
            progress_file.unlink(missing_ok=True)
        except Exception:
            pass


_active_thread = None


def _start_job(job_type: str, module: str, extra_args: list = None):

    global _active_thread

    # Auto-reset se thread morreu mas status ainda é "running"
    if _current_job["status"] == "running":
        thread_alive = _active_thread is not None and _active_thread.is_alive()
        if not thread_alive:
            with _job_lock:
                _current_job["status"] = "error"
                _current_job["finished_at"] = _time.time()
                _current_job["error"] = "Job interrompido inesperadamente."
        else:
            raise HTTPException(
                status_code=409,
                detail="Já existe um job em execução. Aguarde terminar."
            )

    from core.utils.runner_pid import read_runner_pid
    from core.services.process_manager_service import _is_process_alive

    pid = read_runner_pid()
    if pid is not None and _is_process_alive(pid):
        raise HTTPException(
            status_code=409,
            detail="O bot está em execução. Pare o bot antes de rodar o optimizer ou backtest."
        )

    t = _threading.Thread(
        target=_run_job_subprocess,
        args=(job_type, module, extra_args or []),
        daemon=True
    )
    _active_thread = t
    t.start()

    return {"started": True, "type": job_type}


def _extract_summary(result, job_type: str) -> dict:
    """Extrai métricas chave do resultado para o histórico."""
    if not result:
        return {}
    try:
        if job_type == "optimizer" and isinstance(result, list) and result:
            best = max(result, key=lambda x: x.get("score", 0))
            p = best.get("params", best)
            m = best.get("metrics", {})
            return {
                "tp": p.get("atr_take_profit_multiplier"),
                "sl": p.get("atr_stop_multiplier"),
                "trailing": p.get("atr_trailing_multiplier"),
                "score": round(best.get("score", 0), 2),
                "winrate": round(m.get("winrate", 0) * 100, 1),
                "pnl": round(m.get("pnl", 0), 2),
            }
        if job_type == "backtest" and isinstance(result, dict):
            return {
                "winrate": round(result.get("winrate", 0) * 100, 1),
                "pnl": round(result.get("pnl", 0), 2),
                "total_trades": result.get("total_trades"),
                "profit_factor": round(result.get("profit_factor", 0), 2),
            }
    except Exception:
        pass
    return {}


@app.get("/jobs/estimate")
async def jobs_estimate(jtype: str = "optimizer", days: int = 90):
    """
    Estima tempo de execução baseado no histórico real.
    Se não há histórico, retorna None (frontend mostra "—").
    Extrapola proporcionalmente: se 90d levou Xs, 30d leva ~X/3.
    """
    history = _load_history()
    symbols, interval, minimum_rr = _live_job_settings()

    estimate = estimate_job_duration_seconds(
        job_type=jtype,
        days=days,
        symbols=symbols,
        interval=interval,
        minimum_rr=minimum_rr,
        history=history,
    )

    return {
        **estimate,
        "based_on": next(
            (
                h.get("started_at")
                for h in history
                if h.get("type") == jtype
                and h.get("status") == "done"
            ),
            None
        ),
    }


@app.get("/jobs/history")
async def jobs_history(page: int = 1, jtype: str = "all"):
    history = _load_history()

    if jtype in ("optimizer", "backtest"):
        history = [
            item for item in history
            if item.get("type") == jtype
        ]

    per_page = MAX_HISTORY
    total = len(history)
    start = (page - 1) * per_page
    return {
        "items": history[start:start + per_page],
        "total": total,
        "page": page,
        "pages": max(1, (total + per_page - 1) // per_page),
    }


@app.get("/jobs/preview-apply")
async def jobs_preview_apply():
    """Retorna config atual vs nova (best_config.json) para o usuário confirmar."""

    config_path = Path(PROJECT_ROOT_STR) / "core" / "config" / "best_config.json"

    if not config_path.exists():
        raise HTTPException(status_code=404, detail="Rode o optimizer primeiro.")

    with open(config_path, encoding="utf-8") as f:
        best = _json.load(f)

    current_settings = settings_repository.get_settings()

    return {
        "current": {
            "atr_take_profit_multiplier": current_settings.get("atr_take_profit_multiplier"),
            "atr_stop_multiplier":        current_settings.get("atr_stop_multiplier"),
            "atr_trailing_multiplier":    current_settings.get("atr_trailing_multiplier"),
        },
        "new": {
            "atr_take_profit_multiplier": best.get("atr_take_profit_multiplier"),
            "atr_stop_multiplier":        best.get("atr_stop_multiplier"),
            "atr_trailing_multiplier":    best.get("atr_trailing_multiplier"),
        },
    }


@app.get("/jobs/progress")
async def jobs_progress():
    progress_file = (
        Path(PROJECT_ROOT_STR) / "backtest" / "reports" / "progress.json"
    )
    if not progress_file.exists():
        return {"current": 0, "total": 0, "percent": 0, "phase": ""}
    try:
        with open(progress_file, encoding="utf-8") as f:
            return _json.load(f)
    except Exception:
        return {"current": 0, "total": 0, "percent": 0, "phase": ""}


@app.get("/jobs/status")
async def jobs_status():
    with _job_lock:
        job = dict(_current_job)
    elapsed = None
    if job["started_at"]:
        end = job["finished_at"] or _time.time()
        elapsed = round(end - job["started_at"])
    return {**job, "elapsed_seconds": elapsed}


@app.post("/jobs/reset")
async def jobs_reset():
    """Força reset de job travado — use quando 'Já existe um job' após falha."""
    with _job_lock:
        if _current_job["status"] == "running":
            if _active_thread is None or not _active_thread.is_alive():
                _current_job["status"] = "error"
                _current_job["finished_at"] = _time.time()
                _current_job["error"] = "Resetado manualmente."
                return {"reset": True}
    return {"reset": False, "status": _current_job["status"]}


@app.post("/jobs/optimizer")
async def jobs_run_optimizer(days: int = 90):
    extra = ["--days", str(days)] if days in (30, 60, 90) else []
    return _start_job("optimizer", "backtest.optimizer.optimizer_engine", extra)


@app.post("/jobs/backtest")
async def jobs_run_backtest():
    return _start_job("backtest", "backtest.runner")


@app.get("/account/live-balance")
async def account_live_balance():

    """Busca saldo USDT real da Binance (só em modo LIVE)."""

    _s = settings_repository.get_settings()

    if _s.get("mode", "paper") != "live":
        return {"balance": None, "source": "paper", "error": None}

    try:

        from core.services.binance_trading_client import (
            BinanceTradingClient
        )

        # Lê credenciais do .env atualizado, não do objeto settings em memória
        from core.config.settings_repository import (
            _read_raw_lines,
            _parse_current_values
        )
        _env      = _parse_current_values(_read_raw_lines())
        api_key   = _env.get("BINANCE_API_KEY", "").strip()
        api_secret= _env.get("BINANCE_SECRET_KEY", "").strip()
        testnet   = _env.get("BINANCE_TESTNET", "true").strip().lower() in ("1","true","yes","on")
        confirmed = _env.get("LIVE_TRADING_CONFIRMED", "false").strip().lower() in ("1","true","yes","on")

        client = BinanceTradingClient(
            api_key=api_key,
            api_secret=api_secret,
            testnet=testnet,
            live_trading_confirmed=confirmed
        )

        account = await client.get_account_info()
        source = "binance_testnet" if testnet else "binance_mainnet"

        usdt = next(
            (float(b["free"]) for b in account.get("balances", []) if b["asset"] == "USDT"),
            None
        )

        return {
            "balance": round(usdt, 2) if usdt is not None else None,
            "source": source,
            "error": None
        }

    except Exception as e:

        return {
            "balance": None,
            "source": "binance",
            "error": f"Não foi possível buscar saldo: {e}"
        }


@app.post("/jobs/apply")
async def jobs_apply_best_config():

    """
    Aplica o best_config.json gerado pelo último optimizer bem-sucedido
    ao .env (atr_stop_multiplier, atr_take_profit_multiplier,
    atr_trailing_multiplier). O usuário confirma antes de chamar.
    """

    config_path = (
        Path(PROJECT_ROOT_STR) / "core" / "config" / "best_config.json"
    )

    if not config_path.exists():
        raise HTTPException(
            status_code=404,
            detail="Nenhum best_config.json encontrado. Rode o optimizer primeiro."
        )

    with open(config_path, encoding="utf-8") as f:
        best = _json.load(f)

    settings_repository.update_settings(
        atr_stop_multiplier=best.get("atr_stop_multiplier"),
        atr_take_profit_multiplier=best.get("atr_take_profit_multiplier"),
        atr_trailing_multiplier=best.get("atr_trailing_multiplier"),
    )

    return {"applied": True, "config": best}



@app.get(
    "/runtime",
    response_model=RuntimeResponse
)
async def runtime():

    return build_runtime_response()

# =====================================================
# PORTFOLIO
# =====================================================

@app.get(
    "/portfolio",
    response_model=PortfolioResponse
)
async def portfolio():

    latest_snapshot = (

        portfolio_repository
        .get_latest_snapshot(

            user_id=DEFAULT_USER_ID
        )
    )

    return build_portfolio_response(
        latest_snapshot
    )

# =====================================================
# METRICS
# =====================================================

@app.get(
    "/metrics",
    response_model=MetricsResponse
)
async def metrics():

    metrics_data = (

        trade_metrics_service
        .get_metrics(

            user_id=DEFAULT_USER_ID
        )
    )

    return MetricsResponse(
        **metrics_data
    )

# =====================================================
# ADVANCED METRICS
# =====================================================

@app.get(
    "/metrics/advanced",
    response_model=AdvancedMetricsResponse
)
async def advanced_metrics():

    advanced_metrics_data = (

        trade_metrics_service
        .get_advanced_metrics(

            user_id=DEFAULT_USER_ID
        )
    )

    return AdvancedMetricsResponse(
        **advanced_metrics_data
    )

# =====================================================
# RISK STATUS
# =====================================================

@app.get(
    "/risk-status",
    response_model=RiskStatusResponse
)
async def risk_status():

    status = (

        risk_protection_service
        .get_status(

            user_id=DEFAULT_USER_ID,

            account_balance=TRADING_CONFIG[
                "account_balance"
            ]
        )
    )

    return RiskStatusResponse(
        **status
    )

# =====================================================
# OPEN TRADES
# =====================================================

@app.get(
    "/trades/open",
    response_model=List[TradeResponse]
)
async def open_trades():

    open_positions = (

        trades_repository
        .get_open_trades(

            user_id=DEFAULT_USER_ID
        )
    )

    return [

        build_open_trade_response(
            trade
        )

        for trade in open_positions
    ]

# =====================================================
# CLOSED TRADES
# =====================================================

@app.get(
    "/trades/closed",
    response_model=List[TradeResponse]
)
async def closed_trades():

    closed_positions = (

        trades_repository
        .get_closed_trades(

            user_id=DEFAULT_USER_ID
        )
    )

    return [

        build_closed_trade_response(
            trade
        )

        for trade in closed_positions
    ]

# =====================================================
# DASHBOARD
# =====================================================

@app.get(
    "/dashboard",
    response_model=DashboardResponse
)
async def dashboard():

    portfolio_snapshot = (

        portfolio_repository
        .get_latest_snapshot(

            user_id=DEFAULT_USER_ID
        )
    )

    metrics_data = (

        trade_metrics_service
        .get_metrics(

            user_id=DEFAULT_USER_ID
        )
    )

    open_positions = (

        trades_repository
        .get_open_trades(

            user_id=DEFAULT_USER_ID
        )
    )

    closed_positions = (

        trades_repository
        .get_closed_trades(

            user_id=DEFAULT_USER_ID
        )
    )

    return DashboardResponse(

        runtime=build_runtime_response(),

        metrics=MetricsResponse(
            **metrics_data
        ),

        portfolio=build_portfolio_response(
            portfolio_snapshot
        ),

        open_trades=[

            build_open_trade_response(
                trade
            )

            for trade in open_positions
        ],

        recent_closed_trades=[

            build_closed_trade_response(
                trade
            )

            for trade in closed_positions[
                -RECENT_CLOSED_TRADES_LIMIT:
            ]
        ]
    )

# =====================================================
# SETTINGS
# =====================================================

@app.get(
    "/settings",
    response_model=SettingsResponse
)
async def get_settings():

    return settings_repository.get_settings()


@app.put(
    "/settings",
    response_model=SettingsResponse,
    dependencies=[Depends(require_api_token)]
)
@limiter.limit(SENSITIVE_ENDPOINT_RATE_LIMIT)
async def update_settings(
    request: Request,
    payload: SettingsUpdateRequest
):

    # =================================================
    # BLOCK MODE CHANGES WHILE A REAL POSITION IS OPEN
    # =================================================
    #
    # Switching modes restarts the Runner process (MODE is only
    # read once, at Python import time -- there's no in-process way
    # to make a running Runner pick up a changed value otherwise).
    # Restarting while a real position is open would leave that
    # position's lifecycle unmanaged for however long the restart
    # takes, with no agent watching its stop loss/take profit in the
    # interim. This is a hard block, not a warning -- the person
    # must close the position first.

    is_mode_change = (
        payload.mode is not None
    )

    if is_mode_change:

        open_trades = (

            trades_repository
            .get_open_trades(
                user_id=DEFAULT_USER_ID
            )
        )

        if open_trades:

            raise HTTPException(
                status_code=409,

                detail=(
                    "Cannot switch modes while a position is open. "
                    f"Close the {len(open_trades)} open "
                    "position(s) first, then try again."
                )
            )

    # symbols and kline_interval require a restart because the
    # websocket subscription is built once at Runner startup.
    # Mode changes also require a restart to reload settings.py.
    # However: only restart if the runner was already running --
    # never auto-start it if the user had it stopped, since the
    # user controls the runner lifecycle via the web UI (▶ button).
    requires_restart = (
        payload.mode is not None
        or payload.symbols is not None
        or payload.kline_interval is not None
    )

    # Check runner state before saving, so we know whether to
    # restart after. Import here to avoid circular imports at
    # module level.
    from core.utils.runner_pid import read_runner_pid
    from core.services.process_manager_service import _is_process_alive

    _runner_pid = read_runner_pid()
    runner_was_running = (
        _runner_pid is not None
        and _is_process_alive(_runner_pid)
    )

    try:

        updated_settings = (

            settings_repository
            .update_settings(

                mode=payload.mode,
                binance_testnet=payload.binance_testnet,
                binance_api_key=payload.binance_api_key,
                binance_secret_key=payload.binance_secret_key,
                live_trading_confirmed=payload.live_trading_confirmed,
                account_balance=payload.account_balance,

                # Risk
                risk_per_trade_percent=payload.risk_per_trade_percent,
                max_open_positions=payload.max_open_positions,
                max_position_exposure_percent=payload.max_position_exposure_percent,
                minimum_risk_reward_ratio=payload.minimum_risk_reward_ratio,

                # Daily limits
                max_daily_trades=payload.max_daily_trades,
                max_daily_loss_percent=payload.max_daily_loss_percent,
                maximum_daily_drawdown_percent=payload.maximum_daily_drawdown_percent,
                enable_daily_trade_limit=payload.enable_daily_trade_limit,
                enable_daily_loss_limit=payload.enable_daily_loss_limit,
                enable_drawdown_protection=payload.enable_drawdown_protection,

                # Market
                symbols=payload.symbols,
                kline_interval=payload.kline_interval,

                # ATR
                atr_period=payload.atr_period,
                atr_stop_multiplier=payload.atr_stop_multiplier,
                atr_take_profit_multiplier=payload.atr_take_profit_multiplier,
                atr_trailing_multiplier=payload.atr_trailing_multiplier,
                minimum_atr_percent=payload.minimum_atr_percent,

                # Signal quality
                minimum_signal_strength=payload.minimum_signal_strength,
                min_signal_confidence=payload.min_signal_confidence,
                enable_volatility_filter=payload.enable_volatility_filter,
                enable_ema_trend_filter=payload.enable_ema_trend_filter,
                enable_market_regime_alignment=payload.enable_market_regime_alignment,
                enable_signal_cooldown=payload.enable_signal_cooldown,
                signal_cooldown_seconds=payload.signal_cooldown_seconds,

                # Structure
                structure_min_score=payload.structure_min_score,
                structure_min_impulse_percent=payload.structure_min_impulse_percent,
                structure_enable_consolidation_filter=payload.structure_enable_consolidation_filter,

                # Position management
                enable_trailing_stop=payload.enable_trailing_stop,
                enable_breakeven=payload.enable_breakeven,
                breakeven_trigger_percent=payload.breakeven_trigger_percent,
                enable_dynamic_take_profit=payload.enable_dynamic_take_profit,
                dynamic_take_profit_proximity_percent=payload.dynamic_take_profit_proximity_percent,

                # Exchange
                quantity_precision=payload.quantity_precision,
                price_precision=payload.price_precision,
                min_order_quantity=payload.min_order_quantity,
                min_order_notional=payload.min_order_notional,

                # Simulation
                enable_fee_simulation=payload.enable_fee_simulation,
                enable_slippage_simulation=payload.enable_slippage_simulation,
                maker_fee_percent=payload.maker_fee_percent,
                taker_fee_percent=payload.taker_fee_percent,
            )
        )

    except settings_repository.SettingsValidationError as error:

        raise HTTPException(
            status_code=400,

            detail=str(error)
        )

    # =================================================
    # RESTART THE RUNNER WHEN NEEDED
    # =================================================
    #
    # Só reinicia se o bot já estava rodando — se estava parado,
    # salva as configs e deixa o usuário iniciar manualmente pelo ▶

    restart_triggered = False

    if requires_restart and runner_was_running:

        from core.utils.runner_pid import read_runner_pid
        from core.services.process_manager_service import _is_process_alive

        pid = read_runner_pid()
        bot_was_running = (
            pid is not None
            and _is_process_alive(pid)
        )

        if bot_was_running:

            try:

                restart_runner()

                restart_triggered = True

            except ProcessManagerError as error:

                raise HTTPException(
                    status_code=500,

                    detail=(
                        "Configurações salvas, mas falha ao reiniciar o bot: "
                        f"{error}. Reinicie manualmente pelo botão ▶."
                    )
                )

    return {
        **updated_settings,

        "restart_triggered": restart_triggered
    }
