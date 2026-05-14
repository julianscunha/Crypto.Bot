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

```powershell
./scripts/start.ps1
```

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
Exchange Integration ......... 35%
Production Hardening ......... 70%

TOTAL: ~89%
```
