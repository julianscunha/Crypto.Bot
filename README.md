# 🤖 CRYPTO.BOT

<p>
  <img alt="Python" src="https://img.shields.io/badge/python-3.11%2B-3776AB?logo=python&logoColor=white">
  <img alt="Node.js" src="https://img.shields.io/badge/node-20%2B-339933?logo=node.js&logoColor=white">
  <img alt="License" src="https://img.shields.io/badge/license-MIT-blue">
  <img alt="Status" src="https://img.shields.io/badge/status-em%20desenvolvimento-yellow">
  <img alt="Trading Mode" src="https://img.shields.io/badge/live%20trading-experimental-orange">
</p>

Motor de trading algorítmico orientado a eventos, com arquitetura
**multi-agent** e **async**, construído em Python. Ingestão de mercado via
WebSocket da Binance, pipeline de agentes desacoplados (análise → estratégia
→ risco → execução → lifecycle de posição), backtesting/optimizer com dados
históricos reais e um dashboard React para acompanhar tudo em tempo real.

> ⚠️ **Aviso de risco.** Este projeto é oferecido apenas para fins educacionais
> e de pesquisa. Trading de criptoativos envolve risco real de perda de
> capital. O modo `live` (ordens reais na Binance) é experimental e possui
> lacunas conhecidas — veja [Status Atual](#status-atual). Use `paper`
> ou testnet até entender completamente o código e assumir o risco por sua
> conta.

---

## Índice

- [Pré-requisitos](#pré-requisitos)
- [Instalação / Início Rápido](#instalação--início-rápido)
- [Configuração](#configuração)
- [Arquitetura Principal](#arquitetura-principal)
- [Funcionalidades](#funcionalidades)
- [Stack de Trading](#stack-de-trading)
- [Modos de Execução](#modos-de-execução)
- [Console Engine](#console-engine)
- [Frontend](#frontend)
- [Testes](#testes)
- [Banco de Dados](#banco-de-dados)
- [Regras Importantes](#regras-importantes)
- [Status Atual](#status-atual)
- [Documentação completa](#documentação-completa)
- [Licença](#licença)

---

## Pré-requisitos

- **Python 3.11+**
- **Node.js 20+** e **npm** (apenas se for usar o dashboard/frontend)
- **git**
- Uma conta na Binance — opcional, só necessária para o modo `live` ou para
  usar a Testnet da Binance. Nenhuma conta é necessária para rodar em
  `paper` (simulado) ou para backtests.

---

## Instalação / Início Rápido

```bash
git clone https://github.com/julianscunha/Crypto.Bot.git
cd Crypto.Bot

# copie o template de configuração e ajuste os valores
cp .env.example .env
```

Depois de configurar o `.env` (veja [Configuração](#configuração) abaixo),
suba o sistema com o launcher interativo:

Windows:

```powershell
./scripts/start.ps1
```

Linux / macOS:

```bash
./scripts/start.sh
```

Ambos os scripts delegam para o mesmo launcher interativo
(`scripts/bootstrap/launcher.py`), que valida o ambiente, instala as
dependências Python automaticamente (`scripts/bootstrap/requirements.txt`) e
mostra um menu:

```text
[1] Runner       -> apps.trader.runner (paper/live trading)
[2] Optimizer    -> backtest.optimizer.optimizer_engine
[3] Backtest     -> backtest.runner
[4] Frontend     -> npm run dev (frontend/)
[5] Full Stack   -> API + Runner + Frontend
```

`Full Stack` sobe a API (`apps.api.main`, via uvicorn em
`http://127.0.0.1:8000`), o Runner e o Frontend
(`http://localhost:5173`) juntos. Se `frontend/node_modules` estiver
ausente (um checkout novo nunca tem — não é versionado), o launcher roda
`npm install` automaticamente antes de iniciar o dev server. Se `frontend/`
não existir ou `npm` não for encontrado, ele registra um aviso e continua
rodando só com API + Runner — o Full Stack nunca depende do frontend
existir.

---

## Configuração

Toda a configuração vive no `.env` (nunca commitado — veja `.env.example`
para o template completo com todos os valores). As variáveis mais
importantes:

| Variável | Padrão | O que faz |
|---|---|---|
| `MODE` | `paper` | `paper` simula execuções; `live` tenta ordens reais (veja trava abaixo). |
| `BINANCE_TESTNET` | `true` | `true` usa a Testnet da Binance; `false` aponta para mainnet. |
| `BINANCE_API_KEY` / `BINANCE_SECRET_KEY` | vazio | Credenciais da API da Binance. Deixe vazio para rodar só em `paper`. |
| `LIVE_TRADING_CONFIRMED` | `false` | Trava explícita e separada de `MODE`/`BINANCE_TESTNET`. Só com as três condições juntas (`MODE=live`, `BINANCE_TESTNET=false`, `LIVE_TRADING_CONFIRMED=true`) o bot chega a enviar ordens reais em dinheiro real. |
| `ACCOUNT_BALANCE` | `100.0` | Saldo usado pelo motor de risco para dimensionar posições. |
| `SYMBOLS` | `BTCUSDT,ETHUSDT,SOLUSDT` | Pares monitorados. |
| `KLINE_INTERVAL` | `1m` | Timeframe dos candles. |

**Nunca coloque credenciais reais no `.env.example`** nem em qualquer
arquivo commitado — o `.env` real já está no `.gitignore` e não deve ser
versionado.

Você também pode gerenciar Binance API key/secret e o modo de execução pela
aba **Settings** do dashboard, em vez de editar o `.env` manualmente.

---

## Arquitetura Principal

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

## Funcionalidades

- Engine orientada a eventos, async
- Trading multi-symbol
- Isolamento multi-tenant (`user_id`)
- Engine de volatilidade ATR
- Validação de tendência EMA
- Validação de market structure
- Gestão de risco
- Engine de trailing stop
- Analytics de portfolio
- Métricas de runtime
- Ingestão via WebSocket da Binance
- Engine de replay para backtest
- Arquitetura pronta para IA

---

## Stack de Trading

- Python 3.11
- AsyncIO
- SQLAlchemy
- SQLite
- Alembic
- Binance Websocket
- EventBus Architecture

---

## Modos de Execução

- **PAPER** — execuções simuladas, sem conexão de ordens reais. Modo padrão e recomendado para explorar o projeto.
- **LIVE** — ordens reais na Binance. Experimental, com lacunas conhecidas (veja [Status Atual](#status-atual)) e travado por design atrás de `LIVE_TRADING_CONFIRMED`.
- **BACKTEST** — replay de dados históricos via `backtest/runner.py` / Optimizer.

---

## Console Engine

Padronização visual institucional:

- Branco → eventos neutros
- Verde → eventos positivos
- Vermelho → erros/bloqueios
- Amarelo → warnings/trailing

---

## Frontend

Um dashboard de monitoramento em React + Vite vive em `frontend/`. O
launcher (`[4]`/`[5]` no menu) instala as dependências e o inicia
automaticamente. Para rodar isoladamente:

```bash
cd frontend
npm install
npm run dev
```

Abra `http://localhost:5173`. Duas páginas:

- **Monitor** — equity/PnL/drawdown do portfolio em tempo real, win rate,
  trades abertos e recém-fechados, atividade do pipeline de sinais, gráfico
  de PnL, status de risco diário (banner de circuit breaker) e performance
  ajustada a risco (Sharpe, Sortino, max drawdown, streaks). Atualiza a
  cada 3-5s.
- **Settings** — Binance API key/secret (Testnet ou mainnet), seletor de
  modo de trading (Paper/Live, com modal de confirmação e reinício
  automático do bot ao trocar — bloqueado enquanto houver posição aberta).
  Segredos nunca são reenviados pela API depois de salvos — só se um valor
  está definido ou não.

O frontend fala com a API pela URL definida em `frontend/.env`
(`VITE_API_BASE_URL`, padrão `http://127.0.0.1:8000`). A API permite CORS
apenas para a origem do dev server do Vite (`apps/api/main.py`).

---

## Testes

```bash
pip install -r scripts/bootstrap/requirements.txt pytest pytest-asyncio pytest-cov
python -m pytest tests/
```

A suíte de testes usa um banco SQLite, `.env` e arquivos de log isolados e
temporários (veja `tests/conftest.py`) — rodá-la nunca toca o
`data/storage/trades.db`, o `.env` ou os `logs/` reais.

---

## Banco de Dados

```powershell
alembic upgrade head
```

---

## Regras Importantes

Regras de domínio que o código depende para funcionar corretamente — veja
também `CLAUDE.md`/`AGENTS.md` para o detalhe completo:

- Nunca remover `user_id`
- Nunca quebrar payload contracts
- Nunca utilizar `payload.price`
- Utilizar sempre `entry_price`
- Toda comunicação deve passar pelo EventBus
- Todos os agentes devem usar `async def on_message`

---

## Status Atual

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

`Exchange Integration` está em 50% (corrigido de uma estimativa anterior,
não auditada, de 70% -- esses percentuais foram estimados durante o
desenvolvimento sem uma metodologia real, e essa em particular não se
sustentou). A execução real de ordens existe (entrada + OCO protetor +
fallback de fechamento de emergência) e é testada com testes unitários
contra respostas mockadas da Binance, mas três lacunas concretas ainda a
deixam longe de "pronta para produção":

1. **Zero validação contra a API real da Binance** (nem testnet).
2. **Sem rate-limiting no client de ordens** (diferente do fetcher de dados históricos, que já trata `429`).
3. **Sem reconciliação de startup** entre posições/ordens reais na exchange e o banco local.

> **Sobre o `TOTAL: ~85%`.** Esse número (e o de cada módulo) é uma
> autoavaliação qualitativa feita durante o desenvolvimento, não uma métrica
> calculada por alguma metodologia formal (cobertura de linhas, requisitos
> fechados, etc.) — trate como uma indicação aproximada de maturidade
> relativa entre módulos, não como um placar preciso. O que falta para os
> ~15% restantes é essencialmente o que está listado acima em `Exchange
> Integration`, mais o fechamento das lacunas ainda abertas em `Production
> Hardening` e `Persistence Layer`. Não há uma lista fixa e definitiva do que
> soma exatamente até 100% — o roadmap completo (`docs/README_FULL.md`,
> seção `ROADMAP ATUAL`) é a referência mais precisa do que ainda falta.

Veja `LIVE TRADING` em [`docs/README_FULL.md`](docs/README_FULL.md) para o detalhe completo.

---

## Documentação completa

Este README cobre o essencial para rodar o projeto. Para o detalhamento
completo de cada engine, payload contracts, bugs históricos e o motivo por
trás de decisões de design não óbvias, veja
[`docs/README_FULL.md`](docs/README_FULL.md).

---

## Licença

Distribuído sob a licença [MIT](LICENSE).
