# CRYPTO.BOT — FULL DOCUMENTATION

Última atualização: 2026-06-27 18:25

---

# OVERVIEW

Crypto.Bot é uma plataforma modular de trading algorítmico baseada em:

- arquitetura event-driven
- processamento async
- isolamento multi-tenant
- agentes desacoplados
- pipelines operacionais
- engines independentes

---

# SYSTEM FLOW

```text
BinanceWS
    ↓
EventBus
    ↓
AnalystAgent
    ↓
StrategyAgent
    ↓
RiskAgent
    ↓
ExecutionAgent
    ↓
PositionManagerAgent
    ↓
Portfolio Analytics
```

---

# CORE MODULES

## AnalystAgent

Responsável por:
- ingestão analítica
- atualização estrutural
- atualização ATR
- geração de análise inicial

---

## StrategyAgent

Responsável por:
- geração de sinal BUY
- validação ATR
- validação EMA trend
- SignalQualityService
- market structure validation

---

## RiskAgent

Responsável por:
- cálculo ATR risk
- stop loss
- take profit
- trailing stop
- risk/reward
- bloqueios operacionais

---

## ExecutionAgent

Responsável por:
- abertura de trades
- persistência operacional
- registro portfolio
- métricas

---

## PositionManagerAgent

Responsável por:
- trailing stop
- stop loss
- take profit
- unrealized pnl
- lifecycle da posição

---

# EVENT BUS RULES

Todos os agentes devem implementar:

```python
async def on_message(self, message)
```

Toda publicação deve utilizar:

```python
await bus.publish(message)
```

---

# PAYLOAD CONTRACTS

## MarketDataPayload

```python
open
high
low
close
volume
```

---

## StrategySignalPayload

```python
entry_price
signal_strength
atr
```

---

## RiskDecisionPayload

```python
entry_price
stop_loss
take_profit
trailing_stop
risk_reward
```

---

# ATR ENGINE

Features:
- Wilder ATR
- True Range
- volatility filter
- ATR percentage
- real OHLC support

Arquivo:
```text
core/services/atr_service.py
```

---

# MARKET STRUCTURE ENGINE

Features:
- swing detection
- structure validation
- trend strength
- consolidation filter
- fake breakout protection

Arquivos:
```text
core/services/market_structure_service.py
core/config/market_structure_config.py
```

## Configuring the warmup period

`minimum_structure_candles` (default 20) gates every signal until
that many candles have accumulated for a symbol. At a 5m timeframe
with the default, that's ~1h40m of warmup per symbol before any
signal can be generated at all -- if the dashboard shows zero
generated signals with every rejection being `ATR_NOT_READY` /
`NO_STRUCTURE` / `INSUFFICIENT_DATA` / `WEAK_STRUCTURE`, check
whether this warmup has actually elapsed yet before assuming
something is broken.

This setting is read from `.env` under any of these names (first
one set wins, via `core.config.settings.env_int_aliased`):

```text
MINIMUM_STRUCTURE_CANDLES
STRUCTURE_MIN_CANDLES
MIN_STRUCTURE_CANDLES
```

All three exist because `core/config/trading_config.py` and
`core/config/market_structure_config.py` historically read this same
concept from two different, non-overlapping env var names
(`MINIMUM_STRUCTURE_CANDLES` and `STRUCTURE_MIN_CANDLES`
respectively) -- a person setting a third, equally reasonable
variant had it silently ignored, with the system quietly falling
back to the 20-candle default and every signal staying gated far
longer than intended, with no error or warning anywhere. Both
configs now accept all three names consistently.

---

# SIGNAL QUALITY ENGINE

Valida:
- cooldown
- confidence threshold
- EMA trend
- drawdown protection (session-scoped, see DRAWDOWN: SESSION SCOPING)
- max positions
- ATR volatility
- daily loss limit (see DAILY RISK PROTECTION below)
- daily trade limit (see DAILY RISK PROTECTION below)

Arquivo:
```text
core/services/signal_quality_service.py
```

---

# DAILY RISK PROTECTION

`max_daily_loss_percent` and `max_daily_trades` existed in
`core/config/trading_config.py` with sane defaults (and in `.env`)
since early on, but no code anywhere actually read or enforced
them -- they were config in name only. `core/services/
risk_protection_service.py` is what makes them real, as the last two
checks in `SignalQualityService.validate()`'s pipeline.

```text
core/services/risk_protection_service.py
core/config/trading_config.py    -- max_daily_loss_percent, max_daily_trades
core/config/signal_quality_config.py
                                  -- enable_daily_loss_limit,
                                     enable_daily_trade_limit
```

## What it checks

- **Daily loss limit** — sums `Trade.realized_pnl` for every trade
  closed since 00:00 UTC. If the loss (never a profit, regardless of
  size) reaches `max_daily_loss_percent` of the configured
  `account_balance`, no new position opens for the rest of the UTC
  day.
- **Daily trade limit** — counts every trade *opened* since 00:00
  UTC (open or closed, win or loss). Reaching `max_daily_trades`
  blocks further signals even on an active winning streak --
  trading frequency is itself the risk being managed here,
  independent of whether trades so far were profitable.

Both reset automatically at the next UTC day boundary (there's no
explicit "reset" step -- the underlying queries are just naturally
scoped to `closed_at >= today_start` / `created_at >= today_start`).

## Why this is separate from `_validate_drawdown_protection`

That existing check (also in `SignalQualityService`) measures
drawdown **since the current session started** via
`PortfolioSnapshot.drawdown` -- it answers "is the account currently
underwater relative to its session peak". This service answers a
narrower, day-scoped question: "has today specifically gone bad
enough to stop for today", which needs its own UTC-day boundary and
its own automatic reset behavior that the session-scoped check was
never built to express.

## API / Frontend

`GET /risk-status` (`apps/api/schemas/risk_schema.py`) surfaces
`RiskProtectionService.get_status()` for the dashboard's
`RiskStatusBanner` component -- a green banner with today's trade
count when clear, a red banner naming the exact breached limit when
halted.

Covered in `tests/test_risk_protection_service.py`,
`tests/test_signal_quality_service.py`
(`TestValidateDailyLossLimit`, `TestValidateDailyTradeLimit`,
`TestValidatePipelineDailyLimits`), and `tests/test_api.py`
(`TestRiskStatusEndpoint`).

---

# MULTI-TENANT

`user_id` é obrigatório em:
- payloads
- repositories
- metrics
- positions
- analytics

Nunca realizar queries sem `user_id`.

## `reset()` / `reset_all()`

`TradesRepository.reset(user_id)` and `PortfolioRepository.reset(user_id)`
require `user_id` and delete only that user's rows. A separate
`reset_all()` exists on each, deliberately named differently and
intended **only** for the isolated test database
(`tests/conftest.py`'s autouse table-truncation fixture) -- never
for any real code path.

**Real incident this rule exists to prevent:** both `reset()`
methods originally had no `user_id` parameter at all and deleted
every row for every user. `backtest/runner.py` and
`backtest/optimizer/optimizer_engine.py` both call `trades_repository.reset()`
once per backtest pass to clear their own sandbox trades
(`USER_ID = 999`) before each run -- but with no filter, that
wiped real paper-trading history (`user_id=0`) along with it,
silently, every single time either was run. This was caught (twice,
in two separate sessions) only by manually inspecting row counts
before/after -- there was no test that would have caught it,
because no test exercised `reset()` against more than one `user_id`
at a time. `tests/test_trades_repository.py::TestReset::
test_reset_does_not_touch_other_users_trades` is the regression
test for exactly this.

---

# RUNTIME STATE (CROSS-PROCESS TELEMETRY)

`core/state/market_state.py`'s `MarketState` is an in-memory
singleton: `websocket_connected`, `active_symbols`, and every
signal/execution counter live as plain Python attributes on one
object, mutated directly by `data/ingestion/binance_ws.py` and
`core/agents/*`.

That's fine as long as everything runs in one process. It isn't,
under Full Stack: `apps/api/main.py` (uvicorn) and
`apps/trader/runner.py` (the WebSocket + agent pipeline) are started
as **separate OS subprocesses** (see `scripts/bootstrap/launcher.py`'s
`start_fullstack()`). Each gets its own Python interpreter and its
own, completely independent `MarketState` instance. Writes made in
the Runner process are invisible to the API process's copy, forever.

**Symptom this caused:** the dashboard's `/runtime` (and therefore
the Monitor page's "FEED DOWN" badge and signal-pipeline panel) stayed
at its zeroed initial state no matter how long the bot had actually
been running. `websocket_connected` was always `false` even with a
live, connected feed; `active_symbols`, signal counts, and ratios
never moved. It could look like the whole dashboard had stopped
updating, when only this specific cross-process telemetry was stuck
-- portfolio/trade data (already backed by SQLite) updated normally.

**Fix:** a shared `runtime_state` table
(`data/storage/repositories/runtime_state_repository.py`), written
to by the Runner and read by the API:

```text
Runner process                          API process
───────────────                         ───────────
market_state (in-memory)                market_state (in-memory,
     │                                   always empty under Full Stack)
     │ every 2s
     ▼
flush_runtime_state_periodically()
     │
     ▼
runtime_state_repository.upsert(...)  ──▶  runtime_state table  ──▶  runtime_state_repository.get()
   (data/storage/trades.db)                                              │
                                                                          ▼
                                                          MarketState.from_persisted(...)
                                                                          │
                                                                          ▼
                                                                   build_runtime_response()
```

- **Write side** — `apps/trader/runner.py`'s
  `flush_runtime_state_periodically()` runs as a background
  `asyncio` task alongside the WebSocket loop, persisting
  `market_state.snapshot()` to the database every
  `RUNTIME_STATE_FLUSH_INTERVAL_SECONDS` (2s). A failed flush is
  logged as a `WARNING` and never crashes the Runner -- the
  websocket/agent pipeline matters far more than telemetry being
  perfectly current every single flush.
- **Read side** — `apps/api/main.py`'s `build_runtime_response()`
  calls `runtime_state_repository.get()` first. If the Runner has
  flushed at least once, it reconstructs a working `MarketState` via
  `MarketState.from_persisted(...)` (which recalculates
  `uptime_seconds`/ratios from the persisted counters, reusing
  `snapshot()`'s existing logic rather than duplicating it) and
  builds the response from that. If the Runner has never flushed
  (e.g. the API was started standalone, with no Runner at all), it
  falls back to its own local `market_state` so the endpoint still
  returns sane zeroed defaults instead of erroring.

This is always a single overwritten row (`id=1`), not a growing
history -- it's live telemetry, not an audit trail. `EquityCurve`/
`PortfolioSnapshot` already serve the "history over time" role for
portfolio data.

Covered in `tests/test_market_state.py` (`TestFromPersisted`),
`tests/test_runtime_state_repository.py`, `tests/test_trader_runner.py`
(`TestFlushRuntimeStatePeriodically`), and `tests/test_api.py`
(`TestRuntimeEndpoint`'s cross-process simulation tests) -- each
exercising a genuinely separate `MarketState` instance to simulate
the real two-process scenario, not just asserting against the same
object that wrote the data.

---

# DRAWDOWN: SESSION SCOPING

`PortfolioService.build_snapshot()` computes drawdown % against the
true historical peak equity ever reached
(`PortfolioRepository.get_max_equity()`), not just the current
balance/equity -- otherwise drawdown would be understated any time
equity fell from a higher point reached in an earlier snapshot.

That peak lookup is scoped to `PortfolioSnapshot.initial_balance`:
only snapshots recorded under the same configured
`account_balance` (`core/config/trading_config.py`) count toward the
peak for the current calculation.

**Why this matters:** without the scoping, deliberately resetting the
paper account -- e.g. lowering `account_balance` from 100 to 10 --
left old, much higher equity snapshots in the table. The very next
snapshot built after the reset would then compute something like
`(100 - 10) / 100 = 90%` drawdown, even though the account never
actually lost anything; it was reconfigured to a smaller balance on
purpose. `get_max_equity(user_id, initial_balance=None)` (the
default) still returns the unscoped historical max for any existing
caller that doesn't pass `initial_balance` -- only
`PortfolioService.build_snapshot()`'s own internal call passes it,
since that's the one place this distinction actually matters.

A real loss *within* the same session (same `initial_balance`
throughout) is unaffected and still counts normally.

Covered in `tests/test_portfolio_service.py`
(`TestPeakEquitySessionScoping`).

---

# CONSOLE ENGINE

Padronização visual:

## Branco
Eventos neutros:
- MARKET
- STRATEGY
- SYSTEM

## Verde
Eventos positivos:
- SIGNAL BUY
- RISK APPROVED
- EXECUTION OPEN
- TAKE PROFIT

## Vermelho
Eventos negativos:
- BLOCKED
- ERROR
- STOP LOSS

## Amarelo
Eventos intermediários:
- TRAILING STOP
- WARNING

---

# STARTUP PANEL

```text
[SYSTEM] MODE           PAPER
[SYSTEM] SYMBOLS        BTCUSDT ETHUSDT SOLUSDT
[SYSTEM] TIMEFRAME      1m
[SYSTEM] DATABASE       CONNECTED
[SYSTEM] EVENT BUS      READY
[SYSTEM] AGENTS         READY
[SYSTEM] BINANCE        CONNECTED
```

---

# STARTUP / LAUNCHER

Entrypoints (`scripts/start.ps1` on Windows, `scripts/start.sh` on
Linux/macOS) both delegate to the same interactive launcher:

```text
scripts/bootstrap/launcher.py
```

Boot sequence:

```text
cleanup_old_processes()      -- scripts/bootstrap/process_manager.py
        ↓
validate_environment()       -- scripts/bootstrap/validate.py
        ↓
install_requirements()       -- scripts/bootstrap/bootstrap.py
        ↓
show_menu() / runtime loop
```

## validate_environment()

Checks performed:

| Check       | Blocking? | What it verifies                                    |
|-------------|-----------|------------------------------------------------------|
| Python      | Yes       | Python >= 3.11                                       |
| Structure   | Yes       | `apps/`, `core/`, `data/`, `scripts/` exist           |
| Files       | Yes       | `.env` and `scripts/bootstrap/requirements.txt` exist |
| VirtualEnv  | No (warn) | `.venv/` exists                                       |
| Frontend    | No (warn) | `frontend/` exists                                    |

`Frontend` and `VirtualEnv` are informational only — their absence
logs a `WARNING` but never fails `validate_environment()` or blocks
startup. This matters regardless of the frontend's current state in
a given checkout: `start_fullstack()` must never hard-depend on
`frontend/` existing.

## Runtime menu

```text
[1] Runner       -> python -m apps.trader.runner
[2] Optimizer    -> python -m backtest.optimizer.optimizer_engine
[3] Backtest     -> python -m backtest.runner
[4] Frontend     -> npm run dev (cwd=frontend/), only if frontend/ exists
[5] Full Stack   -> API + Runner, plus Frontend if frontend/ exists
[0] Exit
```

## Full Stack (`[5]`)

Starts, as separate OS processes:

1. **API** — `uvicorn apps.api.main:app` on `http://127.0.0.1:8000`
2. **Runner** — `apps.trader.runner` (live paper trading against
   the Binance market-data WebSocket)
3. **Frontend** — only if `frontend/` exists *and* npm dependencies
   can be resolved/installed; otherwise a warning is logged and Full
   Stack continues running with just API + Runner.

`Ctrl+C` terminates all started processes cleanly (`terminate_process()`
sends `SIGTERM`/graceful terminate, then force-kills after a 5s
timeout if a process doesn't exit).

### Frontend startup, step by step

`start_frontend()`/`start_fullstack()` go through three checks before
launching the dev server, each with its own non-crashing fallback:

1. **`frontend_available()`** — does `frontend/` exist at all? If
   not: `warn_frontend_unavailable()`, run with API + Runner only.
2. **`resolve_npm_command()`** — `shutil.which("npm")`. On Windows
   this resolves to `npm.cmd` (the real executable; `npm` itself
   isn't directly invocable via `CreateProcess` without
   `shell=True`). If npm isn't found at all:
   `warn_npm_not_found()`, run with API + Runner only.
3. **`frontend_dependencies_installed()`** — does
   `frontend/node_modules/` exist? It's never shipped (large,
   reproducible). If missing, `install_frontend_dependencies()` runs
   `npm install` in `frontend/` automatically, the same way
   `install_requirements()` does for the Python side. If that
   install fails (non-zero exit code): run with API + Runner only.

Only once all three pass does it actually `Popen` the dev server.

**Bug history**, for context on why all three checks exist
independently:

- `start_fullstack()` originally started the frontend
  unconditionally and crashed with `FileNotFoundError` when
  `frontend/` didn't exist yet (check #1).
- After `frontend/` was built, `subprocess.Popen(["npm", ...])`
  (without `shell=True`) still crashed on Windows specifically with
  `FileNotFoundError ([WinError 2])`, because `npm` there is
  `npm.cmd`, and `CreateProcess` doesn't do the shell's PATHEXT
  resolution (check #2).
- After that fix, a fresh checkout's `frontend/` still had no
  `node_modules/`, so `npm run dev` (which is really just `vite`)
  failed with `'vite' is not recognized...` (Windows) /
  `vite: not found` (Linux) (check #3).

All three are covered in `tests/test_launcher.py`, each isolating
`ROOT` to a temp directory and mocking `shutil.which`/
`subprocess.run`/`subprocess.Popen` rather than depending on whether
a given checkout/CI box happens to have `frontend/`, `npm`, or
`node_modules/` in any particular state.

---

# FRONTEND

```text
frontend/
├── src/
│   ├── api/client.js          -- fetch wrapper for the API
│   ├── hooks/usePolling.js    -- polling hook used by both pages
│   ├── lib/format.js          -- currency/percent/date formatting
│   ├── components/            -- Panel, StatCard, Badge, TradesTable,
│   │                             PnlChart, EventLog
│   └── pages/
│       ├── Dashboard.jsx      -- Monitor page
│       └── Settings.jsx       -- Settings page
└── vite.config.js             -- fixed to port 5173 (matches API CORS)
```

React + Vite. State is fetched via polling (`usePolling`, 3s interval
on the dashboard, 15s on settings) rather than a WebSocket — simpler,
and the API is already a plain REST surface.

## Monitor (`pages/Dashboard.jsx`)

Renders `GET /dashboard` (runtime + metrics + portfolio + open/closed
trades in one call). Equity, total PnL, drawdown, win rate, open
position count, and expectancy as stat cards; open and recently
closed trades as tables; a PnL-by-trade bar chart; and a signal
pipeline breakdown (executed vs. blocked-signal reasons, from
`runtime.execution_reasons` / `runtime.blocked_signal_reasons`).

Two more panels poll their own endpoints separately (5s interval,
vs. 3s for the main dashboard call -- they change less often):

- **`RiskStatusBanner`** (`GET /risk-status`) — green with today's
  trade count when clear; red naming the exact breached limit
  (`DAILY_LOSS_LIMIT_REACHED` / `DAILY_TRADE_LIMIT_REACHED`) when
  the bot has paused for the day. See DAILY RISK PROTECTION.
- **`AdvancedMetricsPanel`** (`GET /metrics/advanced`) — Sharpe,
  Sortino, all-time max drawdown, profit factor, and current/best
  win and loss streaks. See ADVANCED TRADE ANALYTICS.

## Settings (`pages/Settings.jsx`)

Two panels:

- **Execution mode** — shows Paper as active, Live as
  "Coming soon" with `settings.live_trading_unavailable_reason`
  from the API (kept in sync with whether real execution exists,
  rather than a hardcoded string in the frontend).
- **Wallet API credentials** — Binance **Testnet** key/secret fields.
  Already-set credentials render as a fixed-length mask
  (`binance_api_key_masked`); the real value is never sent back by
  the API after saving. Saving sends only the fields that changed
  (`PUT /settings` with optional fields) so an empty/untouched field
  never accidentally clears a saved key. An explicit "Clear" button
  per field is the only way to remove a saved key.

## Settings API (`core/config/settings_repository.py`)

Reads/writes the real `.env` directly, preserving comments, blank
lines, and key order (a naive `os.environ` dump would destroy all of
that). Key points:

- `mode` accepts `"paper"` or `"live"`. Switching to `"live"` here
  does **not** by itself enable real order placement on mainnet --
  see LIVE TRADING below for the separate, deliberate gate that
  does.
- API key/secret must be exactly 64 characters (Binance's format) or
  an empty string to clear.
- `GET /settings` never returns raw key/secret values, only
  `*_set: bool` and a fixed `••••••••` mask.
- `live_trading_available` is `true` only when BOTH Binance
  credentials are set AND `LIVE_TRADING_CONFIRMED=true` is set in
  `.env` -- neither alone is sufficient, mirroring
  `BinanceTradingClient`'s own gate.

## LIVE TRADING

Real order execution against Binance, end to end: a market BUY
entry, a protective OCO (stop loss + take profit) placed immediately
after, and an automatic Runner restart when switching modes through
the Settings panel.

```text
core/services/binance_trading_client.py    -- authenticated REST client
core/services/execution_router.py          -- paper vs. live decision point
core/services/process_manager_service.py    -- restarts the Runner process
core/utils/runner_pid.py                    -- PID file bridging API <-> Runner
apps/api/main.py                            -- PUT /settings: block + restart
frontend/src/pages/Settings.jsx             -- mode selector + confirm modal
```

### Why a restart is needed to change modes at all

`core/config/settings.py`'s `MODE` / `BINANCE_TESTNET` /
`LIVE_TRADING_CONFIRMED` are read once, at Python import time. A
running Runner process keeps whatever values it started with
regardless of what gets written to `.env` afterward -- there's no
in-process mechanism to make it pick up a changed `MODE`. Restarting
the process is what reloads `settings.py` from the updated `.env`.
`PUT /settings` triggers this automatically (only when `mode` is
actually present in the request -- updating just credentials or
`binance_testnet` doesn't restart anything, since
`execution_router.py` re-reads settings fresh on every `execute()`
call rather than caching them).

### The mainnet safety lock

Reaching mainnet (real funds) requires **both**:
1. `BINANCE_TESTNET=false`
2. `LIVE_TRADING_CONFIRMED=true`

These are deliberately separate from each other and from `MODE`. A
person could set `MODE=live` and `BINANCE_TESTNET=false` in one
`.env` edit while believing they were configuring something else --
that single edit must never be enough to enable real-money order
placement. `LIVE_TRADING_CONFIRMED` has to be set as its own,
explicit step. `BinanceTradingClient.__init__` raises
`MainnetNotConfirmedError` if asked to target mainnet without it --
enforced again at construction time, not just by whatever called it,
in case a future bug in `execution_router.py`'s own check is ever
introduced.

### Live execution sequence

1. **Market BUY entry.** If this fails, nothing has happened yet --
   reject the signal exactly like a validation failure.
2. **Real average fill price** is computed from the order response
   (`cummulativeQuoteQty / executedQty`), never the price the signal
   asked for -- a MARKET order fills at whatever the order book
   gives. Every downstream price (stop loss, take profit) is
   recalculated relative to this real fill, preserving the
   *original risk distance* RiskAgent calculated at signal time.
3. **Protective OCO** (take profit + stop loss together, via
   `POST /api/v3/orderList/oco` -- the current, non-deprecated
   endpoint) is placed using that real fill price.
4. Only after **both** orders succeed does anything get written to
   the local `trades` table.

### The single most dangerous failure mode, and how it's handled

If the entry succeeds but the OCO fails, the account now holds a
**real, unprotected position** -- no stop loss, no take profit, full
exposure to whatever the market does next. This is treated as worse
than any other failure this code can produce, including a fully
failed entry, because real money is already on the table with no
safety net.

The response is an immediate **market SELL** for the same quantity,
accepting whatever slippage that costs -- a small, known, immediate
loss is a vastly better outcome than an unprotected position left
open until a human notices. If that emergency close *also* fails,
this is logged at `ERROR` level with an unmistakable message
("MANUAL INTERVENTION REQUIRED IMMEDIATELY") and a distinct
`ExecutionResult.reason`
(`LIVE_POSITION_UNPROTECTED_MANUAL_ACTION_REQUIRED`) -- there is no
further automated recourse at that point, and the failure must never
be silently indistinguishable from a successfully-handled one.

Covered in `tests/test_execution_router.py`
(`TestUnprotectedPositionHandling`, including the worst-case
double-failure scenario) and `tests/test_binance_trading_client.py`.

### Blocking mode switches with an open position

`PUT /settings` returns `409` if any real position
(`Trade.status == "OPEN"`) exists when `mode` is in the request
payload -- restarting the Runner while a position is open would
leave that position's lifecycle unmanaged (no agent watching its
stop loss/take profit) for however long the restart takes. This is a
hard block, not a warning; the person must close the position first.
Updates that don't touch `mode` are never blocked by this check, even
with a position open.

### The zombie-process bug (found and fixed building this)

Confirmed empirically: when the API process starts the Runner via
`subprocess.Popen` and sends it `SIGTERM`, the child becomes a
zombie until something calls `Popen.wait()`/`.poll()` on it --
`os.kill(pid, 0)` and `ps -p <pid>` **both** continue reporting the
zombie as "alive" indefinitely, since nothing else is positioned to
reap a child of that specific process. `Popen.poll()` returned `-15`
(confirmed terminated) at the exact same real-world moment `ps -p`
still listed the process as running.

`process_manager_service.py` keeps an in-memory handle
(`_managed_process`) to any Runner it itself started, and prefers
`Popen.wait()`/`.poll()` for liveness/termination whenever that
handle exists -- falling back to `os.kill(pid, 0)`/`tasklist` only
when it doesn't (e.g. a Runner started by the original launcher
terminal, not by the API). Before this fix, restarting took
10-15+ seconds (the full graceful-then-force-kill timeout chain,
every time) because the zombie was never detected as dead; after the
fix it completes in well under a second.

Covered in `tests/test_process_manager_service.py`
(`TestZombieProcessHandling`), using a real subprocess rather than a
mock, since the bug is specifically about OS-level process/signal
semantics a mock would paper over.

### What's still manual

Nothing about *alerting* exists yet beyond the console log -- the
`MANUAL INTERVENTION REQUIRED` case above is only as loud as whoever
is watching the terminal/log file at that moment. An external alert
(email, SMS, webhook) for that specific failure path is a reasonable
next addition, not yet built.

---

# TESTING

```bash
pip install -r scripts/bootstrap/requirements.txt pytest pytest-asyncio pytest-cov
python -m pytest tests/
```

Coverage report:

```bash
python -m pytest tests/ --cov=core --cov=data --cov=backtest --cov=apps --cov-report=term-missing
```

`tests/conftest.py` provides two autouse, session-scoped fixtures:

- **Isolated database** — redirects `data.storage.database`'s engine
  and `SessionLocal` to a temporary SQLite file for the whole test
  session, and truncates tables between tests. The real
  `data/storage/trades.db` is never read or written by the suite.
- **Isolated logs** — redirects `runtime_logger`/`error_logger`'s
  file handlers to a temp directory. The real `logs/runtime.log` and
  `logs/errors.log` are never written by the suite.

Coverage spans: EventBus, all repositories, all analyst-side services
(ATR, EMA trend, market structure, market regime, signal quality),
the full agent pipeline (signal → risk → execution → exit), the
backtest engine and optimizer, the validation interpreter, the
FastAPI dashboard, alembic migrations against a fresh database, and
the bootstrap/launcher scripts.

---

# PROJECT STRUCTURE

```text
apps/
core/
data/
backtest/
frontend/
scripts/
alembic/
logs/
```

---

# BACKTEST ENGINE

Fluxo:

```text
CSV
 ↓
ReplayEngine
 ↓
EventBus
 ↓
Agents
 ↓
Metrics
```

Arquivos:
- backtest/engine/replay_engine.py
- backtest/engine/metrics_engine.py
- backtest/engine/report_engine.py

---

# ADVANCED TRADE ANALYTICS

`core/services/trade_analytics.py` holds pure, no-I/O functions over
a list of trade PnLs (equity curve, max drawdown, win/loss streaks,
profit factor, risk/reward, recovery factor, Sharpe, Sortino).
Extracted from `backtest/engine/metrics_engine.py`, which originally
computed these only for backtests, so live trading and backtesting
share one implementation instead of two that could silently drift
apart.

```text
core/services/trade_analytics.py        -- pure functions
core/services/trade_metrics_service.py  -- get_advanced_metrics() (live)
backtest/engine/metrics_engine.py       -- generate() (backtest)
```

**Bug fixed during extraction:** the original backtest implementation
iterated `trades_repository.get_closed_trades()` directly, which
orders results `DESC` by `closed_at` (most recent first). The
equity-curve/streak loop needs chronological (oldest-first) order --
`metrics_engine.py` now explicitly reverses the trade list before
passing it to `compute_equity_curve_stats()`.

## Sharpe / Sortino convention

Both treat each trade's PnL as one "return" observation. There is no
natural per-trade risk-free rate for an intraday paper bot, so both
use the simplified, risk-free-rate-free form common in retail
strategy evaluation: mean return ÷ (downside) deviation of returns.
This is for comparing the bot's own trade-to-trade consistency over
time, not a substitute for instrument-level risk-free benchmarking.
Sortino only penalizes downside deviation -- a sequence with a large
upside outlier scores meaningfully higher than one with an equally
large downside outlier, even with identical means (see
`tests/test_trade_analytics.py::TestComputeSortinoRatio::
test_only_penalizes_downside_not_upside_volatility`).

## `max_drawdown` here vs. `PortfolioResponse.drawdown`

These are deliberately different numbers:

- `trade_analytics.compute_equity_curve_stats()["max_drawdown"]` --
  the true historical peak-to-trough dip across **every closed
  trade ever**, in dollars. Used for `GET /metrics/advanced` and the
  backtest report.
- `PortfolioService`'s session-scoped drawdown (see DRAWDOWN:
  SESSION SCOPING) -- a percentage measured against the peak equity
  reached under the **current account-balance configuration**. Used
  for the live dashboard's main drawdown stat and the daily/session
  circuit breakers.

## API / Frontend

`GET /metrics/advanced`
(`apps/api/schemas/advanced_metrics_schema.py`) surfaces
`TradeMetricsService.get_advanced_metrics()` for the dashboard's
`AdvancedMetricsPanel` component (Sharpe, Sortino, max drawdown,
profit factor, current/best win and loss streaks).

Covered in `tests/test_trade_analytics.py`,
`tests/test_backtest_engine.py` (refactor regression coverage), and
`tests/test_api.py` (`TestAdvancedMetricsEndpoint`).

---

# OPTIMIZER & BACKTEST: REAL HISTORICAL DATA

`backtest/optimizer/optimizer_engine.py`'s `OptimizerEngine` used to
tune parameters against the same small, fixed synthetic CSVs in
`backtest/datasets/` every single run, regardless of how the actual
market had moved since (those files: ~20 candles each, last modified
2026-05-07, plus a 500-row `validation.csv`). It now fetches real
history from Binance's public klines endpoint before every run.

```text
data/ingestion/binance_history.py   -- fetch/paginate/split/write
backtest/optimizer/optimizer_engine.py
                                     -- __init__/_prepare_datasets,
                                        BLOCKING_VERDICTS gate
```

## Fetch

`OptimizerEngine.HISTORY_DAYS` (90) days of `KLINE_INTERVAL`-interval
candles per configured `SYMBOLS`, via the *public*, unauthenticated
`/api/v3/klines` endpoint -- read-only market data, the same kind of
public information `data/ingestion/binance_ws.py`'s WebSocket feed
already reads, not an authenticated trading endpoint. Paginates
(Binance returns at most 1000 candles/call), retries on `429`
respecting `Retry-After`, and retries transient network errors with
exponential backoff.

**Falls back to the synthetic datasets** (with a clear `WARNING` log,
never a crash) if the fetch fails for any reason -- a network hiccup
must never block running an optimization at all, it should just
visibly use weaker data.

## Train/validation split

`OptimizerEngine.VALIDATION_DAYS` (15) of the **most recent** candles
are held out for validation; everything older is training data. This
is a **time split, not a random one**
(`data.ingestion.binance_history.split_train_validation`) --
shuffling candles before splitting would let the optimizer "validate"
against data chronologically interleaved with what it trained on,
which is data leakage: it would make an overfit parameter set look
validated when it was never actually tested against unseen data.

## Validation gate

**Bug fixed:** `core/config/best_config.json` was written
**unconditionally**, *before* walk-forward validation even ran. A
parameter set the optimizer's own validation report flagged as
overfit (`PROMISING_BUT_SUSPICIOUS`) or backed by too little data
(`INSUFFICIENT_DATA`) still got picked up by
`core/config/config_loader.py` on the Runner's next start, exactly as
if it had passed validation cleanly.

Fixed: the save now happens *after* the walk-forward verdict is
known, and is skipped entirely (`OptimizerEngine.BLOCKING_VERDICTS`)
for `PROMISING_BUT_SUSPICIOUS` and `INSUFFICIENT_DATA`. `ROBUST` and
`MODERATE` still save normally. A blocked save leaves whatever
`best_config.json` already existed completely untouched, logging a
`WARNING` explaining why instead.

Covered in `tests/test_binance_history.py` and
`tests/test_optimizer_engine.py` (`TestPrepareDatasetsFallback`,
`TestPrepareDatasetsSuccess`, `TestValidationGate`).

## Backtest (`backtest/runner.py`)

`backtest/runner.py` (menu option `[3]`) is a **separate** entrypoint
from the optimizer -- it evaluates the currently configured strategy
against history rather than tuning parameters, so it originally had
its own hardcoded `DATASETS` list pointing at the same synthetic
CSVs, completely disconnected from the optimizer's real-data fetch.

**Bug fixed:** running the optimizer first picked up real Binance
history (as designed), but running Backtest afterward still silently
used the old synthetic datasets -- the two entrypoints were never
actually connected, so fixing one didn't fix the other.

Backtest now calls its own `prepare_datasets()` (mirroring
`OptimizerEngine._prepare_datasets()`), fetching `HISTORY_DAYS` (90)
days of real history per symbol with the same fallback-to-synthetic
behavior on failure. No train/validation split here, unlike the
optimizer -- Backtest is evaluating the current strategy against
real history, not selecting parameters, so there's no
"validating against the same data it trained on" risk to guard
against.

**Second bug fixed during this integration:** the first version of
`prepare_datasets()` called `asyncio.run()` internally, but it's
invoked from inside `main()` -- itself an `async` function already
running inside its own `asyncio.run(main())` at the real entrypoint
(`if __name__ == "__main__": asyncio.run(main())`). Calling
`asyncio.run()` again from an already-running event loop raises
`RuntimeError: asyncio.run() cannot be called from a running event
loop` -- which `prepare_datasets()`'s own `except Exception` caught
and silently swallowed. The practical effect: every real run fell
back to the synthetic datasets unconditionally, regardless of
network availability, because the real fetch was never actually
*able* to run at all, not because it failed. Fixed by making
`prepare_datasets()` itself `async` and `await`-ing it directly from
`main()`, with no nested `asyncio.run()` anywhere in the call chain.

Output files use a `_backtest.csv` suffix
(`backtest/datasets/live_history/{symbol}_backtest.csv`), distinct
from the optimizer's `_train.csv`/`_validation.csv` in the same
shared directory -- no filename collision between the two
entrypoints' fetches.

Covered in `tests/test_backtest_runner.py`
(`TestPrepareDatasets`, including
`test_does_not_raise_runtime_error_when_called_from_a_running_loop`,
the regression test for the asyncio nesting bug specifically).

---

# CURRENT ROADMAP

## Próximos módulos

- External alerting for the unprotected-position failure path (see
  LIVE TRADING above -- currently console-log only)
- PostgreSQL
- Redis streams
- distributed locking
- retry engine
- AI signal optimization

---

# IMPORTANT RULES

- Não quebrar state machine
- Não remover validações
- Não ignorar `user_id`
- Não misturar payload contracts
- Não criar session global
- Não manter transaction aberta
- Manter arquitetura async consistente

---

# CURRENT STATUS

```text
Core Infrastructure .......... 96%
Trading Engine ............... 93%
Lifecycle Engine ............. 94%
Portfolio Engine ............. 90%
Persistence Layer ............ 84%
Exchange Integration ......... 50%
Risk & Analytics ............. 85%
Production Hardening ......... 75%

TOTAL: ~85%
```

`Exchange Integration` at 50% (corrected from an earlier, unaudited
70% estimate -- these percentages were eyeballed during development
rather than calculated against real criteria, and that one in
particular didn't hold up): the entry/OCO/emergency-close sequence
exists and is unit-tested against mocked Binance responses, but
three concrete gaps keep it well short of "ready":

1. **Zero validation against the real Binance API**, not even
   testnet -- this development sandbox has no network access to
   `api.binance.com` or `testnet.binance.vision` at all. Every test
   so far mocks the HTTP layer.
2. **No rate-limit handling in `binance_trading_client.py`** -- unlike
   `binance_history.py` (which retries on `429` with backoff), the
   order-placement client has none. A rate limit hit during a fast
   market move -- exactly when timely execution matters most --
   currently just fails outright.
3. **No startup reconciliation** -- the original design called for
   checking the exchange's real open orders/positions against the
   local database when the Runner starts in live mode, and that was
   never built. If the bot restarts with a real position already
   open on the exchange, nothing currently checks for that before
   resuming normal operation.
