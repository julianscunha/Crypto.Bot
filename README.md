# CRYPTO.BOT

Motor de trading algorítmico orientado a eventos com arquitetura multi-agent async.

---

## Core Architecture

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
```

---

## Features

- Async event-driven engine
- Multi-symbol trading
- Multi-tenant isolation (`user_id`)
- ATR volatility engine
- EMA trend validation
- Market structure validation
- Risk management
- Trailing stop engine
- Portfolio analytics
- Runtime metrics
- Binance websocket ingestion
- Backtest replay engine
- AI-ready architecture

---

## Trading Stack

- Python 3.11
- AsyncIO
- SQLAlchemy
- SQLite
- Alembic
- Binance Websocket
- EventBus Architecture

---

## Runtime Modes

- PAPER
- LIVE (planned)
- BACKTEST

---

## Console Engine

Padronização visual institucional:

- Branco → eventos neutros
- Verde → eventos positivos
- Vermelho → erros/bloqueios
- Amarelo → warnings/trailing

---

## Startup

Windows:

```powershell
./scripts/start.ps1
```

Linux / macOS:

```bash
./scripts/start.sh
```

Both scripts delegate to the same interactive launcher
(`scripts/bootstrap/launcher.py`), which validates the environment,
installs dependencies, and shows a runtime menu:

```text
[1] Runner       -> apps.trader.runner (live paper trading)
[2] Optimizer    -> backtest.optimizer.optimizer_engine
[3] Backtest     -> backtest.runner
[4] Frontend     -> npm run dev (frontend/)
[5] Full Stack   -> API + Runner + Frontend
```

`Full Stack` starts the API (`apps.api.main`, served via uvicorn on
`http://127.0.0.1:8000`), the Runner, and the Frontend
(`http://localhost:5173`) together. If `frontend/node_modules` is
missing (a fresh checkout never has it — it's not shipped), the
launcher runs `npm install` automatically before starting the dev
server. If `frontend/` is ever removed or `npm` isn't found at all,
it logs a warning and keeps running with just the API + Runner —
Full Stack never depends on the frontend existing.

---

## Frontend

A React + Vite monitoring dashboard lives in `frontend/`. The
launcher (`[4]`/`[5]` in the menu) installs dependencies and starts
it automatically. To run it standalone instead:

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`. Two pages:

- **Monitor** — live portfolio equity/PnL/drawdown, win rate, open
  and recently closed trades, signal pipeline activity, a PnL chart,
  daily risk status (circuit breaker banner), and risk-adjusted
  performance (Sharpe, Sortino, max drawdown, streaks). Polls the
  API every 3-5s.
- **Settings** — Binance API key/secret (Testnet or mainnet),
  trading mode selector (Paper/Live, with a confirmation modal and
  automatic bot restart on switch — blocked while any position is
  open). Secrets are never echoed back by the API after saving —
  only whether one is set.

The frontend talks to the API at the URL in `frontend/.env`
(`VITE_API_BASE_URL`, defaults to `http://127.0.0.1:8000`). The API
allows CORS from the Vite dev server origin only
(`apps/api/main.py`).

---

## Tests

```bash
pip install -r scripts/bootstrap/requirements.txt pytest pytest-asyncio pytest-cov
python -m pytest tests/
```

The test suite uses an isolated temporary SQLite database, `.env`
file, and log files (see `tests/conftest.py`) — running it never
touches the real `data/storage/trades.db`, `.env`, or `logs/` files.

---

## Database

```powershell
alembic upgrade head
```

---

## Important Rules

- Nunca remover `user_id`
- Nunca quebrar payload contracts
- Nunca utilizar `payload.price`
- Utilizar sempre `entry_price`
- Toda comunicação deve passar pelo EventBus
- Todos os agentes devem usar `async def on_message`

---

## Current Status

```text
Core Infrastructure .......... 96%
Trading Engine ............... 93%
Lifecycle Engine ............. 94%
Portfolio Engine ............. 90%
Persistence Layer ............ 84%
Exchange Integration ......... 50%
Risk & Analytics ............. 85%
Production Hardening ......... 75%
Frontend ..................... 60%

TOTAL: ~85%
```

`Exchange Integration` is at 50% (corrected from an earlier,
unaudited 70% -- these percentages were eyeballed during development
without a real methodology, and that estimate didn't hold up).
Real order execution exists (entry + protective OCO + an
emergency-close fallback) and is unit-tested against mocked Binance
responses, but three concrete things still keep it short of ready:
zero validation against the real Binance API (not even testnet --
this dev environment has no network access to Binance at all), no
rate-limit handling in the order-placement client specifically
(unlike the historical-data fetcher, which has it), and no
startup reconciliation between the exchange's real open
orders/positions and the local database. See LIVE TRADING in
README_FULL.md for the full detail.
