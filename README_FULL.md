# CRYPTO.BOT

## Overview

Crypto.Bot é uma plataforma modular de trading algorítmico orientada a eventos, baseada em arquitetura async/event-driven com isolamento multi-tenant via `user_id`.

---

# Architecture

## Event Flow

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

# Core Stack

- Python 3.11
- AsyncIO
- SQLAlchemy
- Alembic
- SQLite
- Event-Driven Architecture
- Multi-Agent Trading Engine

---

# Current Features

## Trading Engine

- Multi-symbol
- BUY signal flow
- Risk management
- Position lifecycle
- Portfolio analytics
- Async message bus

---

# Position Lifecycle Engine

## States

- OPEN
- ACTIVE
- TAKE_PROFIT
- STOP_LOSS
- CLOSED

## Features

- trailing stop
- stop loss
- take profit
- pnl realization
- breakeven preparation

---

# Async Hardening

## Implementado

- coroutine-safe event bus
- exception isolation
- subscriber protection
- await validation

---

# Contract Stabilization

## Padrão Oficial

MarketDataPayload:
- open
- high
- low
- close
- volume

StrategySignalPayload:
- entry_price

RiskDecisionPayload:
- entry_price
- risk_reward

Nunca utilizar:
- payload.price

---

# Multi-Tenant

`user_id` é obrigatório em:

- payloads
- repositories
- positions
- metrics
- analytics

Nunca realizar queries sem `user_id`.

---

# Event Bus

## Rules

Todos os agentes devem usar:

```python
async def on_message(self, message)
```

E:

```python
await bus.publish(message)
```

---

# Database

## Stack

- SQLAlchemy ORM
- Alembic migrations
- SQLite

## Migration

```powershell
alembic upgrade head
```

---

# Project Structure

```text
apps/
core/
data/
alembic/
scripts/
```

---

# Main Modules

## core/

- agents/
- bus/
- contracts/
- services/

## data/

- ingestion/
- storage/

---

# Portfolio Analytics

## Current Metrics

- total_trades
- winrate
- pnl
- equity curve

---

# Current Operational Status

```text
Core Infrastructure .......... 90%
Trading Engine ............... 84%
Lifecycle Engine ............. 86%
Portfolio Engine ............. 80%
Exchange Integration ......... 25%
Risk Infrastructure .......... 82%
Production Hardening ......... 42%

TOTAL: ~81%
```

---

# Known Issues

- BinanceWS ainda mockado
- Sem orderbook real
- Sem exchange execution real
- Sem distributed lock
- Sem retry engine robusto
- Necessário hardening async completo

---

# Next Priorities

- Exchange Adapter real Binance
- Websocket real
- PostgreSQL
- Redis event streaming
- Distributed locking
- Strategy engine avançado
- Backtesting
- AI-assisted signals

---

# Important Rules

- Não quebrar state machine
- Não remover validações
- Não ignorar user_id
- Não misturar payload contracts
- Manter arquitetura async consistente