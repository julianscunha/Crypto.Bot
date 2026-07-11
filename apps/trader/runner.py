# -*- coding: utf-8 -*-

import asyncio

import atexit

import signal

from core.utils.runner_pid import (
    write_runner_pid,
    clear_runner_pid
)

from core.bus.event_bus import (
    EventBus
)

from core.agents.analyst_agent import (
    AnalystAgent
)

from core.agents.strategy_agent import (
    StrategyAgent
)

from core.agents.risk_agent import (
    RiskAgent
)

from core.agents.execution_agent import (
    ExecutionAgent
)

from core.agents.position_manager_agent import (
    PositionManagerAgent
)

from data.ingestion.binance_ws import (
    BinanceWS
)

from data.storage.database import (
    init_db
)

from core.config.config_loader import (
    load_best_config
)

from core.utils.console_logger import (
    log,
    print_section
)

from backtest.reports.report_renderer import (
    ReportRenderer
)

from core.services.portfolio_service import (
    PortfolioService
)

from core.config.trading_config import (
    TRADING_CONFIG
)

from core.config.settings import (
    settings
)

from core.state.market_state import (
    market_state
)

from data.storage.repositories.runtime_state_repository import (
    runtime_state_repository
)


# =========================================================
# SYSTEM PANEL
# =========================================================

def print_system_panel():

    from core.config.trading_config import TRADING_CONFIG
    from core.config.trade_management_config import TRADE_MANAGEMENT_CONFIG
    from core.services.runtime_balance import get_balance

    mode    = settings.MODE.upper()
    testnet = getattr(settings, 'BINANCE_TESTNET', True)
    mode_label = f"LIVE {'TESTNET' if testnet else 'MAINNET ⚠'}" if mode == 'LIVE' else 'PAPER'
    mode_level = 'SUCCESS' if (mode == 'LIVE' and testnet) else 'WARNING'

    # Em modo LIVE, main() já chamou set_balance() com o saldo real
    # da Binance antes de chegar aqui -- ler TRADING_CONFIG direto
    # mostraria o valor estático do .env (ACCOUNT_BALANCE), que pode
    # divergir muito do saldo real (ex.: .env com $101 configurado,
    # conta testnet real com $2.97). get_balance() com fallback para
    # TRADING_CONFIG cobre o caso PAPER, onde nenhum fetch acontece.
    balance    = get_balance(TRADING_CONFIG.get('account_balance', 0))
    risk       = TRADING_CONFIG.get('risk_per_trade_percent', 0)
    rr_min     = TRADING_CONFIG.get('minimum_risk_reward_ratio', 0)
    max_pos    = getattr(settings, 'MAX_OPEN_POSITIONS', '?')
    risk_amt   = round(balance * risk / 100, 4)
    max_trades = TRADING_CONFIG.get('max_daily_trades', '?')
    max_loss   = TRADING_CONFIG.get('max_daily_loss_percent', '?')
    max_dd     = TRADING_CONFIG.get('maximum_daily_drawdown_percent', '?')

    try:
        import json as _json
        from pathlib import Path as _Path
        bc_path = _Path('core/config/best_config.json')
        if bc_path.exists():
            bc     = _json.loads(bc_path.read_text(encoding='utf-8'))
            params = bc.get('params', bc)
            tp = params.get('atr_take_profit_multiplier', TRADING_CONFIG.get('atr_take_profit_multiplier', '?'))
            sl = params.get('atr_stop_multiplier',        TRADING_CONFIG.get('atr_stop_multiplier', '?'))
            tr = params.get('atr_trailing_multiplier',    TRADE_MANAGEMENT_CONFIG.get('atr_trailing_multiplier', '?'))
        else:
            tp = TRADING_CONFIG.get('atr_take_profit_multiplier', '?')
            sl = TRADING_CONFIG.get('atr_stop_multiplier', '?')
            tr = TRADE_MANAGEMENT_CONFIG.get('atr_trailing_multiplier', '?')
        rr_val = round(tp / sl, 2) if isinstance(tp, (int,float)) and isinstance(sl, (int,float)) and sl > 0 else '?'
    except Exception:
        tp = sl = tr = rr_val = '?'

    print_section('CRYPTO.BOT ENGINE')

    log('SYSTEM', f'MODO           {mode_label}', mode_level)
    log('SYSTEM', f'PARES          {" | ".join(settings.SYMBOLS)}')
    log('SYSTEM', f'TIMEFRAME      {settings.KLINE_INTERVAL}')
    print()
    log('SYSTEM', f'SALDO          ${balance}')
    log('SYSTEM', f'RISCO/TRADE    {risk}%  →  ${risk_amt} por trade')
    log('SYSTEM', f'RR MÍNIMO      {rr_min}')
    log('SYSTEM', f'MÁX. POSIÇÕES  {max_pos}')
    log('SYSTEM', f'ATR            TP×{tp}  SL×{sl}  TRAILING×{tr}  RR={rr_val}')
    log('SYSTEM', f'LIMITES        trades={max_trades}  perda={max_loss}%  drawdown={max_dd}%')
    print()
    log('SYSTEM', 'DATABASE       CONNECTED', 'SUCCESS')
    log('SYSTEM', 'EVENT BUS      READY',     'SUCCESS')
    log('SYSTEM', 'AGENTS         READY',     'SUCCESS')

# =========================================================
# AGENTS
# =========================================================

def initialize_agents(
    bus
):

    AnalystAgent(bus)

    StrategyAgent(bus)

    RiskAgent(bus)

    ExecutionAgent(bus)

    PositionManagerAgent(bus)

# =========================================================
# SESSION REPORT
# =========================================================

def print_session_report():

    from core.services.runtime_balance import get_balance

    portfolio_service = (
        PortfolioService()
    )

    portfolio_snapshot = (

        portfolio_service
        .build_snapshot(

            user_id=0,

            # Mesmo raciocínio de print_system_panel(): em LIVE, o
            # saldo real da Binance (buscado no startup) deve ser a
            # base do relatório, não o valor estático do .env.
            initial_balance=get_balance(
                TRADING_CONFIG[
                    "account_balance"
                ]
            )
        )
    )

    runtime_snapshot = (
        market_state.snapshot()
    )

    ReportRenderer.print_header(
        "LIVE SESSION REPORT"
    )

    # =====================================================
    # SESSION
    # =====================================================

    ReportRenderer.print_section(
        "SESSION"
    )

    ReportRenderer.print_metric(
        "Balance",
        portfolio_snapshot.balance
    )

    ReportRenderer.print_metric(
        "Equity",
        portfolio_snapshot.equity
    )

    ReportRenderer.print_metric(
        "Realized PnL",
        portfolio_snapshot.realized_pnl
    )

    ReportRenderer.print_metric(
        "Unrealized PnL",
        portfolio_snapshot.unrealized_pnl
    )

    ReportRenderer.print_metric(
        "Total PnL",
        portfolio_snapshot.total_pnl
    )

    ReportRenderer.print_metric(
        "Open Positions",
        portfolio_snapshot.open_positions
    )

    ReportRenderer.print_metric(
        "Closed Positions",
        portfolio_snapshot.closed_positions
    )

    ReportRenderer.print_metric(
        "Exposure",
        portfolio_snapshot.exposure
    )

    ReportRenderer.print_metric(
        "Drawdown",
        f"{portfolio_snapshot.drawdown}%"
    )

    # =====================================================
    # BLOCKED SIGNALS
    # =====================================================

    blocked_reasons = (
        runtime_snapshot[
            "blocked_signal_reasons"
        ]
    )

    if blocked_reasons:

        ReportRenderer.print_section(
            "BLOCKED SIGNALS"
        )

        for reason, count in sorted(
            blocked_reasons.items(),
            key=lambda item: item[1],
            reverse=True
        ):

            ReportRenderer.print_metric(
                reason,
                count
            )

    # =====================================================
    # MARKET PIPELINE
    # =====================================================

    ReportRenderer.print_section(
        "MARKET"
    )

    ReportRenderer.print_metric(
        "Market Messages",
        runtime_snapshot[
            "total_market_messages"
        ]
    )

    ReportRenderer.print_metric(
        "Analysis Requests",
        runtime_snapshot[
            "total_analysis_requests"
        ]
    )

    ReportRenderer.print_metric(
        "Generated Signals",
        runtime_snapshot[
            "total_generated_signals"
        ]
    )

    ReportRenderer.print_metric(
        "Approved Signals",
        runtime_snapshot[
            "total_approved_signals"
        ]
    )

    ReportRenderer.print_metric(
        "Rejected Signals",
        runtime_snapshot[
            "total_rejected_signals"
        ]
    )

    ReportRenderer.print_metric(
        "Signal Generation Ratio",
        (
            f"{runtime_snapshot['signal_generation_ratio']}%"
        )
    )

    ReportRenderer.print_metric(
        "Signal Approval Ratio",
        (
            f"{runtime_snapshot['signal_approval_ratio']}%"
        )
    )

    ReportRenderer.print_metric(
        "Websocket",
        (
            "CONNECTED"
            if runtime_snapshot[
                "websocket_connected"
            ]
            else "DISCONNECTED"
        )
    )

    ReportRenderer.print_metric(
        "Active Symbols",
        len(
            runtime_snapshot[
                "active_symbols"
            ]
        )
    )

    ReportRenderer.print_metric(
        "Uptime (sec)",
        runtime_snapshot[
            "uptime_seconds"
        ]
    )

    ReportRenderer.print_footer()

    print()

# =========================================================
# RUNTIME STATE FLUSH
# =========================================================
#
# market_state is an in-memory singleton local to this process.
# Under Full Stack (scripts/bootstrap/launcher.py), the API runs as
# a SEPARATE OS process and has its own, permanently-empty copy --
# it never sees writes made here. This task periodically persists
# this process's market_state to the database so the API can read
# real telemetry (websocket_connected, active_symbols, signal
# counters) instead of always reporting the zeroed defaults,
# regardless of how long the bot has actually been running.
#
# A short interval (2s) keeps the dashboard feeling live without
# writing to SQLite on every single market message/signal -- WAL
# mode (see data/storage/database.py) makes this cheap regardless,
# but there's no reason to flush more often than the frontend polls
# the API for it (every 3s -- see frontend/src/pages/Dashboard.jsx).

RUNTIME_STATE_FLUSH_INTERVAL_SECONDS = 2


async def flush_runtime_state_periodically():

    while True:

        await asyncio.sleep(
            RUNTIME_STATE_FLUSH_INTERVAL_SECONDS
        )

        try:

            runtime_state_repository.upsert(
                market_state.snapshot()
            )

        except Exception as error:

            log(
                "SYSTEM",
                (
                    "RUNTIME STATE FLUSH FAILED "
                    f"{error}"
                ),
                "WARNING"
            )

# =========================================================
# PORTFOLIO SNAPSHOT (BACKGROUND)
# =========================================================
#
# portfolio_service.build_snapshot() used to be called ONLY from
# print_session_report(), i.e. once, at Runner shutdown. Every read
# the Dashboard does (GET /dashboard, GET /portfolio) just returns
# the latest row in the portfolio_snapshots table -- so while the bot
# was running, Equity/Balance on the Dashboard stayed frozen at
# whatever they were the last time the bot was STOPPED, potentially
# stale by days and completely disconnected from the real, currently
# changing Binance balance. This periodically writes a fresh
# snapshot instead, same pattern as flush_runtime_state_periodically()
# above. create_snapshot() always INSERTS a new row (it's an
# append-only history table, used by get_max_equity() for the
# all-time peak) -- 30s keeps the Dashboard reasonably live without
# the granularity (and DB growth) of the 2s runtime-state flush,
# which upserts a single row instead.

PORTFOLIO_SNAPSHOT_INTERVAL_SECONDS = 30


def _write_portfolio_snapshot():

    from core.services.runtime_balance import get_balance

    PortfolioService().build_snapshot(
        user_id=0,
        initial_balance=get_balance(
            TRADING_CONFIG["account_balance"]
        )
    )


async def flush_portfolio_snapshot_periodically():

    while True:

        try:

            _write_portfolio_snapshot()

        except Exception as error:

            log(
                "SYSTEM",
                (
                    "PORTFOLIO SNAPSHOT FLUSH FAILED "
                    f"{error}"
                ),
                "WARNING"
            )

        await asyncio.sleep(
            PORTFOLIO_SNAPSHOT_INTERVAL_SECONDS
        )

# =========================================================
# MAIN
# =========================================================

def _get_env_mode() -> str:
    """Lê MODE do .env em tempo real para não depender do objeto settings."""
    try:
        from core.config.settings_repository import ENV_PATH
        for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("MODE=") and not line.startswith("#"):
                return line.split("=", 1)[1].strip().strip('"').strip("'").lower()
        return "paper"
    except Exception as e:
        log("SYSTEM", f"_get_env_mode falhou: {e} — usando {settings.MODE}", "WARNING")
        return settings.MODE.lower()


async def main():

    # =====================================================
    # DATABASE
    # =====================================================

    init_db()

    # =====================================================
    # CONFIG
    # =====================================================

    # Carrega config silenciosamente — as infos aparecem no painel ENGINE
    import io as _io
    import sys as _sys
    _null = _io.StringIO()
    _sys.stdout, _old_stdout = _null, _sys.stdout
    try:
        load_best_config()
    finally:
        _sys.stdout = _old_stdout

    # Saldo inicial: valor do .env (sobrescrito pela Binance em LIVE)
    from core.services.runtime_balance import set_balance
    from core.config.trading_config import TRADING_CONFIG
    set_balance(TRADING_CONFIG.get("account_balance", 0.0))

    # =====================================================
    # LIVE BALANCE SYNC
    # =====================================================
    #
    # Em modo LIVE, busca o saldo USDT real da Binance e
    # atualiza ACCOUNT_BALANCE no .env automaticamente.
    # Em modo PAPER, usa o valor configurado manualmente.

    _current_mode = _get_env_mode()

    log("SYSTEM", f"MODO DETECTADO: {_current_mode.upper()}")

    if _current_mode == "live":

        try:

            from core.services.binance_trading_client import (
                BinanceTradingClient
            )


            client = BinanceTradingClient(

                api_key=settings.BINANCE_API_KEY,

                api_secret=settings.BINANCE_SECRET_KEY,

                testnet=settings.BINANCE_TESTNET,

                live_trading_confirmed=(
                    settings.LIVE_TRADING_CONFIRMED
                )
            )

            account = (
                await client.get_account_info()
            )

            usdt_balance = next(
                (
                    float(b["free"])
                    for b in account.get("balances", [])
                    if b["asset"] == "USDT"
                ),
                None
            )

            if usdt_balance is not None:

                from core.services.runtime_balance import set_balance
                set_balance(usdt_balance)

                log(
                    "SYSTEM",
                    f"Saldo USDT da Binance: ${usdt_balance:.2f}",
                    "SUCCESS"
                )

            # Carregar filtros reais (stepSize, tickSize) por símbolo
            from core.services.exchange_filters import load_filters

            await load_filters(
                client=client,
                symbols=settings.SYMBOLS
            )

            # Reconciliar estado da exchange com banco local
            from core.services.startup_reconciler import reconcile_on_startup

            await reconcile_on_startup(client, symbols=settings.SYMBOLS)

        except Exception as error:

            log(
                "SYSTEM",
                (
                    f"Falha ao buscar saldo da Binance: {error} — "
                    "usando valor configurado em ACCOUNT_BALANCE"
                ),
                "WARNING"
            )

    # =====================================================
    # SYSTEM PANEL
    # =====================================================

    print_system_panel()

    # =====================================================
    # EVENT BUS
    # =====================================================

    bus = EventBus()

    # =====================================================
    # AGENTS
    # =====================================================

    initialize_agents(
        bus
    )

    # =====================================================
    # WEBSOCKET
    # =====================================================

    websocket = BinanceWS(

        bus=bus,

        user_id=0
    )

    # =====================================================
    # RUNTIME STATE FLUSH (BACKGROUND)
    # =====================================================

    flush_task = asyncio.create_task(
        flush_runtime_state_periodically()
    )

    portfolio_flush_task = asyncio.create_task(
        flush_portfolio_snapshot_periodically()
    )

    try:

        await websocket.start()

    finally:

        flush_task.cancel()

        portfolio_flush_task.cancel()

        # Final, best-effort flush -- the periodic task above only
        # persists every RUNTIME_STATE_FLUSH_INTERVAL_SECONDS, so
        # without this the API can keep reporting a stale
        # websocket_connected=True (or stale counters) for up to
        # that long after the process has actually stopped.
        try:

            market_state.set_websocket_connected(
                False
            )

            runtime_state_repository.upsert(
                market_state.snapshot()
            )

        except Exception as error:

            log(
                "SYSTEM",
                f"RUNTIME STATE FINAL FLUSH FAILED {error}",
                "WARNING"
            )

# =========================================================
# GRACEFUL SHUTDOWN (SIGINT / SIGTERM)
# =========================================================
#
# asyncio.run() already turns Ctrl+C into KeyboardInterrupt, which
# main()'s own `finally` (above) and the except block below already
# handle -- but that path never reaches an `await`-based cleanup, it
# just unwinds. SIGTERM (sent by `docker stop`, `kill`, a process
# manager, or Task Manager's "End task") has no such built-in
# handling in asyncio at all -- left alone, it kills the process
# immediately, skipping flush_task.cancel() and the final runtime
# state flush entirely. Installing an explicit handler for both
# signals routes them through the exact same coroutine-level
# cancellation, so shutdown behaves identically regardless of which
# signal triggered it.
#
# loop.add_signal_handler is POSIX-only (NotImplementedError on
# Windows, including with the Selector event loop this project
# already requires for aiohttp -- see core/utils/event_loop.py).
# signal.signal() works on Windows for SIGTERM specifically (unlike
# SIGTERM's not-quite-equivalent-signals story on some other
# platforms), so it's used as the fallback there.

async def _run_with_graceful_shutdown():

    loop = asyncio.get_running_loop()

    main_task = asyncio.ensure_future(
        main()
    )

    def _request_shutdown(sig_name):

        log(
            "SYSTEM",
            f"Sinal {sig_name} recebido — iniciando shutdown gracioso...",
            "WARNING"
        )

        main_task.cancel()

    for sig_name in ("SIGTERM", "SIGINT"):

        sig = getattr(
            signal,
            sig_name,
            None
        )

        if sig is None:
            continue

        try:

            loop.add_signal_handler(
                sig,
                _request_shutdown,
                sig_name
            )

        except NotImplementedError:

            signal.signal(
                sig,
                lambda signum, frame, name=sig_name: (
                    loop.call_soon_threadsafe(
                        _request_shutdown,
                        name
                    )
                )
            )

    try:

        await main_task

    except asyncio.CancelledError:

        pass

# =========================================================
# ENTRYPOINT
# =========================================================

if __name__ == "__main__":

    write_runner_pid()

    atexit.register(
        clear_runner_pid
    )

    try:

        # aiohttp requires SelectorEventLoop on Windows -- see
        # core/utils/event_loop.py for the full explanation.
        from core.utils.event_loop import configure_event_loop

        configure_event_loop()

        asyncio.run(
            _run_with_graceful_shutdown()
        )

        log(
            "SYSTEM",
            "Shutdown...................... OK",
            "WARNING"
        )

        print_session_report()

    except KeyboardInterrupt:

        log(
            "SYSTEM",
            "Shutdown...................... OK",
            "WARNING"
        )

        print_session_report()
