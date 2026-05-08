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

### PAPER MODE (mock/random feed)

signal_quality_config.py

- cooldown_seconds = 5
- ema_fast_period = 9
- ema_slow_period = 21
- min_atr_percent = 0.40

market_structure_config.py

- swing_window = 2
- min_trend_strength = 1
- consolidation_threshold = 0.001

---

### REAL MARKET MODE (Binance Kline)

signal_quality_config.py

- cooldown_seconds = 15
- ema_fast_period = 9
- ema_slow_period = 21
- min_atr_percent = 0.60

market_structure_config.py

- swing_window = 3
- min_trend_strength = 2
- consolidation_threshold = 0.003

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
Core Infrastructure .......... 96%
Trading Engine ............... 93%
Lifecycle Engine ............. 94%
Portfolio Engine ............. 90%
Persistence Layer ............ 84%
Exchange Integration ......... 35%
Production Hardening ......... 70%

TOTAL: ~89%
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

---

# Repository Layer

## Current Architecture

- Stateless repositories
- Session-per-operation
- Transaction isolation
- Rollback safety
- Lifecycle-safe persistence

## Repository Rules

Nunca manter:
- session global
- session persistente
- transaction aberta entre eventos

# =========================================================
# PORTFOLIO CONSISTENCY ENGINE
# =========================================================

## COMPONENTS

- PortfolioSnapshot
- PortfolioRepository
- PortfolioService
- Equity Tracking
- Exposure Tracking
- Drawdown Engine
- Unrealized PnL Tracking

## FLOW

OPEN TRADE
    -> snapshot update

PRICE UPDATE
    -> unrealized pnl update

CLOSE TRADE
    -> realized pnl update

## METRICS

- equity
- exposure
- drawdown
- realized pnl
- unrealized pnl
- total pnl
- open positions
- closed positions


# =========================================================
# SIGNAL QUALITY ENGINE
# =========================================================

## COMPONENTS

- SignalQualityService
- Confidence Threshold
- Cooldown Engine
- Drawdown Protection
- Position Limiter
- Frontend Config Ready

## FLOW

StrategySignal
    -> SignalQualityService
    -> RiskAgent
    -> ExecutionAgent

## VALIDATIONS

- confidence threshold
- cooldown validation
- max open positions
- drawdown guard

## FRONTEND READY

Arquivo:
core/config/signal_quality_config.py

Variáveis:
- confidence_threshold
- cooldown_seconds
- max_open_positions
- daily_drawdown_limit
- ema_fast_period
- ema_slow_period
- min_atr_percent

Todos os parâmetros podem ser:
- editados manualmente
- controlados pelo frontend
- ajustados por IA
- persistidos futuramente em banco


# =========================================================
# EMA TREND ENGINE
# =========================================================

## COMPONENTS

- EmaTrendService
- EMA Fast
- EMA Slow
- Bullish Trend Validation

## FLOW

MarketData
    -> update_price()
    -> EMA Calculation
    -> Trend Validation
    -> SignalQualityService

## VALIDATION

BUY permitido apenas quando:

EMA_FAST > EMA_SLOW

## CONFIG

Arquivo:
core/config/signal_quality_config.py

Variáveis:
- ema_fast_period
- ema_slow_period
- enable_trend_filter


## REAL MARKET STRUCTURE ENGINE

Engine responsável por validação estrutural de tendência.

Features:
- Swing High Detection
- Swing Low Detection
- Trend Strength
- Break of Structure
- Consolidation Filter
- Fake Breakout Prevention

Arquivos:
- core/services/market_structure_service.py
- core/config/market_structure_config.py

## REAL BINANCE KLINE ENGINE

Engine responsável por ingestão real de candles Binance.

Features:
- Websocket Binance
- Real OHLC
- Closed Candle Validation
- Multi-symbol streaming
- Real volume
- Real EMA input
- Real market structure input

Arquivo:
- data/ingestion/binance_ws.py


## REAL ATR ENGINE

Engine responsável por volatilidade real baseada em OHLC.

Features:
- True Range
- Wilder ATR
- ATR Percent
- Volatility Filter
- Multi-user safe
- Binance Kline compatible

Arquivos:
- core/services/atr_service.py

# BACKTEST ENGINE REAL

Sistema de replay histórico utilizando:
- EventBus real
- Agents reais
- Strategy real
- Risk real
- Position Manager real

Fluxo:
CSV → ReplayEngine → EventBus → Agents → Metrics

Arquivos:
- backtest/engine/replay_engine.py
- backtest/engine/metrics_engine.py
- backtest/engine/report_engine.py
- backtest/runner.py