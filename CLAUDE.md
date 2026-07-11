# CLAUDE.md

Convenções gerais de estrutura, build/test, estilo de código e PR já estão em `AGENTS.md` — leia-o também. Este arquivo cobre arquitetura e regras de domínio que não devem ser violadas.

## Arquitetura

Motor de trading orientado a eventos, multi-agent, async (Python 3.11):

```
BinanceWS → EventBus → AnalystAgent → StrategyAgent → RiskAgent → ExecutionAgent → PositionManagerAgent
```

- `apps/` — entry points (`apps/api` FastAPI, `apps/trader` runner).
- `core/agents/` — cada agente herda `base_agent` e implementa `async def on_message`. Toda comunicação entre agentes passa pelo `core/bus` (EventBus) — nunca chame um agente diretamente.
- `core/config/` — configs tipadas (ATR, EMA, market structure, regimes em `core/config/regimes/`, `best_config.json`).
- `data/storage/` — models SQLAlchemy + `trades.db` (SQLite). `data/ingestion/` — WebSocket da Binance.
- `backtest/` — engine, optimizer, runner; fixtures em `backtest/datasets/`.
- `frontend/` — dashboard React + Vite (`Monitor`, `Operação`, `Ferramentas`, `Configurações`), fala com a API via `VITE_API_BASE_URL`.
- Detalhe completo de status/roadmap em `docs/README_FULL.md`.

## Regras de domínio (nunca violar)

- Nunca remover `user_id` dos payloads — o sistema é multi-tenant.
- Nunca usar `payload.price`; usar sempre `entry_price`.
- Toda comunicação entre agentes passa pelo EventBus.
- Todo agente implementa `async def on_message`.

## Runtime modes

- `MODE=paper|live` no `.env`. Mesmo com `MODE=live` e `BINANCE_TESTNET=false`, ordens reais só saem se `LIVE_TRADING_CONFIRMED=true` também estiver setado — é uma trava proposital separada do `MODE`.
- Exchange Integration está em ~78%: rate-limit no client de ordens e reconciliação de startup (`core/services/startup_reconciler.py`) já existem. **Ainda falta**: validação real contra a API da Binance (nem testnet — sem acesso de rede neste ambiente de dev); ver checklist manual em `docs/README_FULL.md`.

## Testes

- `python -m pytest tests/` usa banco SQLite, `.env` e logs isolados/temporários (`tests/conftest.py`) — nunca toca `data/storage/trades.db`, `.env` ou `logs/` reais.

## Console Engine (padrão visual de logs)

Branco = neutro, verde = positivo, vermelho = erro/bloqueio, amarelo = warning/trailing.

Cada processo grava em seu próprio arquivo (`logs/runtime.log` = API/launcher,
`logs/runtime-runner.log` = Runner, `logs/runtime-<job>.log` = Optimizer/Backtest)
— nunca compartilhe um arquivo de log entre processos: escritas concorrentes de
processos diferentes no mesmo arquivo corrompem/derrubam linhas silenciosamente,
sem lançar exceção (ver `core/utils/console_logger.py`).
