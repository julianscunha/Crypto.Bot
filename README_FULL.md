# CRYPTO.BOT — MASTER DOCUMENT

## Visão Geral
Sistema profissional de trading automatizado baseado em:
- Multi-agentes (Work Room)
- Arquitetura event-driven
- State machine de trades
- Orchestrator central
- IA plugável (futuro)
- Multi-tenant (user_id isolado)

## Estados do Trade
IDLE → ANALYZING → SIGNAL_GENERATED → RISK_APPROVED → ORDER_SENT → ORDER_FILLED → POSITION_OPEN → POSITION_CLOSED

## Modos
- Paper Trading
- Live Trading

## Segurança
- user_id obrigatório
- isolamento total
- validação tipada

## Roadmap
- Binance integração
- Paper trading real
- UI
- IA
