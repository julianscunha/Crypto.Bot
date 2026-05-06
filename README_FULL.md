# CRYPTO.BOT — MASTER ARCHITECTURE DOCUMENT

## Visão Geral

Crypto.Bot é um sistema profissional de automação de trade em criptomoedas baseado em:

- Arquitetura event-driven
- Multi-agentes (WorkRoom)
- Engine de execução
- Persistência de trades
- Métricas operacionais
- Risk engine
- State machine
- Runtime unificado
- Preparação para IA futura
- Multi-tenant via user_id

Objetivo principal:
transformar sinais operacionais em edge estatística consistente.

---

# Arquitetura Geral

Market Data
↓
Analyst Agent
↓
Strategy Agent
↓
Risk Agent
↓
Execution Agent
↓
Persistence
↓
Metrics Engine

---

# Runtime

EntryPoint:
apps/main.py

Responsável por:
- subir API FastAPI
- iniciar trader runtime
- controlar multiprocessing
- lifecycle/shutdown
- runtime unificado

---

# Estrutura Atual do Projeto

crypto.bot/

├── apps/
├── core/
├── data/
├── infra/
├── scripts/
├── requirements.txt
├── README.md
├── README_FULL.md
└── PROJECT_PROMPT.txt

---

# Core Atual Implementado

## Event Driven
- EventBus
- publish/subscribe
- mensagens tipadas

## Trading Engine
- Strategy Engine
- Risk Engine
- Execution Engine

## Persistência
- SQLite
- trades
- positions
- metrics

## Indicadores
- EMA 9
- EMA 21
- RSI 14
- ATR 14

## Risk
- stop loss
- take profit
- dynamic sizing
- volatility filter

## Metrics
- pnl
- winrate
- total trades

## Multi-Symbol Engine (IMPLEMENTED)

Symbols:
- BTCUSDT
- ETHUSDT
- SOLUSDT
- BNBUSDT

Features:
- multi-symbol runtime
- isolated positions
- symbol-aware contracts
- portfolio-ready architecture

Position isolation:
positions[user_id][symbol]

Arquivos:
core/contracts/messages.py
data/ingestion/binance_ws.py
data/storage/positions_repository.py
core/agents/strategy_agent.py
core/agents/risk_agent.py
core/agents/execution_agent.py

## Trailing Stop + Breakeven (IMPLEMENTED)

Features:
- dynamic trailing stop
- breakeven protection
- ATR-based risk management
- symbol-aware risk engine

Rules:
- breakeven at 1R
- trailing stop using ATR
- dynamic stop update
- isolated position management

Arquivos:
core/agents/risk_agent.py
core/agents/execution_agent.py
data/storage/positions_repository.py
data/storage/database.py

# =========================================================
# PORTFOLIO ANALYTICS (IMPLEMENTED)
# =========================================================

Features:
- equity curve
- realized pnl
- unrealized pnl
- max drawdown
- profit factor
- average win/loss
- portfolio analytics

Arquivos:
- data/storage/equity_repository.py
- data/storage/metrics.py
- data/storage/database.py
- core/agents/execution_agent.py

Tables:
- equity_curve

Metrics:
- equity
- drawdown
- profit factor
- avg win
- avg loss
- winrate

Architecture:
portfolio-aware analytics engine

# =========================================================
# DATABASE MIGRATIONS (IMPLEMENTED)
# =========================================================

Stack:
- SQLAlchemy
- Alembic

Features:
- schema versioning
- auto migration
- migration history
- schema evolution
- production-ready persistence

Arquivos:
- alembic.ini
- alembic/env.py
- data/storage/models.py
- scripts/migrate.py

Comandos:
alembic revision --autogenerate -m "migration_name"
alembic upgrade head

Objetivo:
eliminar schema drift entre código e SQLite

# =========================================================
# SQLALCHEMY MIGRATION (IMPLEMENTED)
# =========================================================

Storage Layer:
- SQLAlchemy ORM
- Alembic migrations
- SessionLocal architecture
- ORM repositories
- schema versioning

Repositories:
- positions_repository.py
- equity_repository.py
- metrics.py

Objetivo:
eliminar sqlite3 procedural layer

---

# Fluxo Operacional

BinanceWS
↓
MarketDataMessage
↓
AnalystAgent
↓
StrategySignalMessage
↓
RiskDecisionMessage
↓
ExecutionAgent
↓
Database

---

# Objetivo Atual

Transformar sinais em edge estatística:
- reduzir ruído
- reduzir overtrading
- melhorar consistência
- melhorar expectancy

---

# Próximos Passos

## Engine
- trailing stop
- breakeven
- equity curve
- exposure engine

## Strategy
- multi timeframe
- market structure
- volume profile

## Metrics
- sharpe
- profit factor
- drawdown

## Infra
- Binance real
- UI profissional
- IA colaborativa

---

# Regras Arquiteturais

- não remover user_id
- não quebrar contracts
- não quebrar state machine
- manter event-driven
- manter isolamento por usuário
