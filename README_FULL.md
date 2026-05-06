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
