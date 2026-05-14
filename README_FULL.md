# CRYPTO.BOT — FULL DOCUMENTATION

Última atualização: 2026-05-14 19:23

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

---

# SIGNAL QUALITY ENGINE

Valida:
- cooldown
- confidence threshold
- EMA trend
- drawdown protection
- max positions
- ATR volatility

Arquivo:
```text
core/services/signal_quality_service.py
```

---

# MULTI-TENANT

`user_id` é obrigatório em:
- payloads
- repositories
- metrics
- positions
- analytics

Nunca realizar queries sem `user_id`.

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

# PROJECT STRUCTURE

```text
apps/
core/
data/
backtest/
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

# CURRENT ROADMAP

## Próximos módulos

- Binance execution real
- PostgreSQL
- Redis streams
- distributed locking
- retry engine
- AI signal optimization
- frontend operational dashboard
- optimizer engine
- live portfolio monitoring

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
Exchange Integration ......... 35%
Production Hardening ......... 70%

TOTAL: ~89%
```
