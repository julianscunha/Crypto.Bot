# CRYPTO.BOT — DOCUMENTAÇÃO COMPLETA

Última atualização: 2026-06-27 18:25

---

# VISÃO GERAL

Crypto.Bot é uma plataforma modular de trading algorítmico baseada em:

- arquitetura event-driven
- processamento async
- isolamento multi-tenant
- agentes desacoplados
- pipelines operacionais
- engines independentes

---

# FLUXO DO SISTEMA

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

# MÓDULOS PRINCIPAIS

## AnalystAgent

Responsável por:
- ingestão analítica
- atualização estrutural
- atualização de ATR
- geração de análise inicial

---

## StrategyAgent

Responsável por:
- geração de sinal BUY
- validação de ATR
- validação de EMA trend
- SignalQualityService
- market structure validation

---

## RiskAgent

Responsável por:
- cálculo de ATR risk
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
- registro de portfolio
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

# REGRAS DO EVENT BUS

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
- suporte a OHLC real

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

## Configurando o período de warmup

`minimum_structure_candles` (padrão 20) trava todo sinal até que essa
quantidade de candles tenha se acumulado para um símbolo. Num timeframe
de 5m com o padrão, isso equivale a ~1h40 de warmup por símbolo antes
de qualquer sinal poder ser gerado — se o dashboard mostrar zero sinais
gerados com toda rejeição sendo `ATR_NOT_READY` / `NO_STRUCTURE` /
`INSUFFICIENT_DATA` / `WEAK_STRUCTURE`, verifique se esse warmup já
decorreu antes de assumir que algo está quebrado.

Esse valor é lido do `.env` sob qualquer um destes nomes (o primeiro
que estiver definido vence, via `core.config.settings.env_int_aliased`):

```text
MINIMUM_STRUCTURE_CANDLES
STRUCTURE_MIN_CANDLES
MIN_STRUCTURE_CANDLES
```

Os três existem porque `core/config/trading_config.py` e
`core/config/market_structure_config.py` historicamente liam esse
mesmo conceito a partir de dois nomes de variável de ambiente
diferentes e não sobrepostos (`MINIMUM_STRUCTURE_CANDLES` e
`STRUCTURE_MIN_CANDLES`, respectivamente) — quem configurasse uma
terceira variante, igualmente razoável, tinha o valor silenciosamente
ignorado, com o sistema caindo de volta ao padrão de 20 candles e
todo sinal ficando travado por muito mais tempo do que o pretendido,
sem nenhum erro ou aviso em lugar nenhum. Ambas as configs agora
aceitam os três nomes de forma consistente.

---

# SIGNAL QUALITY ENGINE

Valida:
- cooldown
- confidence threshold
- EMA trend
- drawdown protection (com escopo de sessão, ver DRAWDOWN: ESCOPO DE SESSÃO)
- max positions
- ATR volatility
- daily loss limit (ver PROTEÇÃO DE RISCO DIÁRIA abaixo)
- daily trade limit (ver PROTEÇÃO DE RISCO DIÁRIA abaixo)

Arquivo:
```text
core/services/signal_quality_service.py
```

---

# PROTEÇÃO DE RISCO DIÁRIA

`max_daily_loss_percent` e `max_daily_trades` existiam em
`core/config/trading_config.py` com padrões sensatos (e no `.env`)
desde cedo, mas nenhum código em lugar nenhum de fato os lia ou
aplicava — eram config apenas no nome. `core/services/
risk_protection_service.py` é o que os torna reais, como as duas
últimas verificações no pipeline de `SignalQualityService.validate()`.

```text
core/services/risk_protection_service.py
core/config/trading_config.py    -- max_daily_loss_percent, max_daily_trades
core/config/signal_quality_config.py
                                  -- enable_daily_loss_limit,
                                     enable_daily_trade_limit
```

## O que verifica

- **Daily loss limit** — soma `Trade.realized_pnl` de todo trade
  fechado desde 00:00 UTC. Se a perda (nunca um lucro, independente
  do tamanho) atingir `max_daily_loss_percent` do `account_balance`
  configurado, nenhuma posição nova abre pelo resto do dia UTC.
- **Daily trade limit** — conta todo trade *aberto* desde 00:00 UTC
  (aberto ou fechado, ganho ou perda). Atingir `max_daily_trades`
  bloqueia novos sinais mesmo numa sequência de vitórias ativa — a
  frequência de trading em si é o risco sendo gerenciado aqui,
  independente de os trades até então terem sido lucrativos.

Ambos resetam automaticamente na próxima virada de dia UTC (não há um
passo explícito de "reset" — as queries subjacentes simplesmente já
são escopadas para `closed_at >= today_start` / `created_at >= today_start`).

## Por que isso é separado de `_validate_drawdown_protection`

Aquela verificação existente (também em `SignalQualityService`) mede
o drawdown **desde o início da sessão atual** via
`PortfolioSnapshot.drawdown` — ela responde "a conta está atualmente
no negativo em relação ao pico da sessão". Esse serviço responde uma
pergunta mais estreita, escopada por dia: "o dia de hoje especificamente
ficou ruim o suficiente para parar por hoje", o que precisa do seu
próprio limite de dia UTC e do seu próprio comportamento de reset
automático, que a verificação escopada por sessão nunca foi construída
para expressar.

## API / Frontend

`GET /risk-status` (`apps/api/schemas/risk_schema.py`) expõe
`RiskProtectionService.get_status()` para o `RiskStatusBanner` do
dashboard — um banner verde com a contagem de trades de hoje quando
tudo está liberado, um banner vermelho nomeando o limite exato
violado quando pausado.

Coberto em `tests/test_risk_protection_service.py`,
`tests/test_signal_quality_service.py`
(`TestValidateDailyLossLimit`, `TestValidateDailyTradeLimit`,
`TestValidatePipelineDailyLimits`) e `tests/test_api.py`
(`TestRiskStatusEndpoint`).

---

# MULTI-TENANT

`user_id` é obrigatório em:
- payloads
- repositories
- metrics
- positions
- analytics

Nunca realizar queries sem `user_id`.

## `reset()` / `reset_all()`

`TradesRepository.reset(user_id)` e `PortfolioRepository.reset(user_id)`
exigem `user_id` e deletam apenas as linhas daquele usuário. Existe um
`reset_all()` separado em cada um, deliberadamente nomeado diferente,
destinado **apenas** ao banco de dados isolado de testes (a fixture
autouse de truncagem de tabelas em `tests/conftest.py`) — nunca para
nenhum caminho de código real.

**Incidente real que essa regra existe para prevenir:** ambos os
métodos `reset()` originalmente não tinham nenhum parâmetro `user_id`
e deletavam toda linha de todo usuário. `backtest/runner.py` e
`backtest/optimizer/optimizer_engine.py` chamam `trades_repository.reset()`
uma vez por passada de backtest para limpar seus próprios trades de
sandbox (`USER_ID = 999`) antes de cada execução — mas sem filtro,
isso apagava o histórico real de paper trading (`user_id=0`) junto,
silenciosamente, toda vez que qualquer um dos dois era executado. Isso
só foi detectado (duas vezes, em duas sessões separadas) inspecionando
manualmente contagens de linhas antes/depois — não havia teste que
pegaria isso, porque nenhum teste exercitava `reset()` contra mais de
um `user_id` ao mesmo tempo. `tests/test_trades_repository.py::TestReset::
test_reset_does_not_touch_other_users_trades` é o teste de regressão
para exatamente esse caso.

---

# RUNTIME STATE (TELEMETRIA CROSS-PROCESS)

`core/state/market_state.py`'s `MarketState` é um singleton em memória:
`websocket_connected`, `active_symbols` e todo contador de
sinal/execução vivem como atributos Python simples em um único objeto,
mutados diretamente por `data/ingestion/binance_ws.py` e
`core/agents/*`.

Isso funciona bem enquanto tudo roda em um único processo. Não é o
caso no Full Stack: `apps/api/main.py` (uvicorn) e
`apps/trader/runner.py` (o pipeline de WebSocket + agentes) são
iniciados como **subprocessos de SO separados** (ver
`scripts/bootstrap/launcher.py`'s `start_fullstack()`). Cada um recebe
seu próprio interpretador Python e sua própria instância de
`MarketState`, completamente independente. Escritas feitas no
processo Runner são invisíveis à cópia do processo da API, para
sempre.

**Sintoma que isso causava:** o `/runtime` do dashboard (e, portanto,
o badge "FEED DOWN" da página Monitor e o painel de pipeline de
sinais) ficava travado no estado zerado inicial, não importa há
quanto tempo o bot estivesse de fato rodando. `websocket_connected`
sempre ficava `false` mesmo com um feed conectado e ao vivo;
`active_symbols`, contagens de sinal e ratios nunca se moviam. Podia
parecer que o dashboard inteiro tinha parado de atualizar, quando na
verdade só essa telemetria cross-process específica estava travada —
dados de portfolio/trade (já apoiados em SQLite) atualizavam
normalmente.

**Correção:** uma tabela `runtime_state` compartilhada
(`data/storage/repositories/runtime_state_repository.py`), escrita
pelo Runner e lida pela API:

```text
Processo Runner                         Processo API
────────────────                        ────────────
market_state (em memória)               market_state (em memória,
     │                                   sempre vazio no Full Stack)
     │ a cada 2s
     ▼
flush_runtime_state_periodically()
     │
     ▼
runtime_state_repository.upsert(...)  ──▶  tabela runtime_state  ──▶  runtime_state_repository.get()
   (data/storage/trades.db)                                              │
                                                                          ▼
                                                          MarketState.from_persisted(...)
                                                                          │
                                                                          ▼
                                                                   build_runtime_response()
```

- **Lado de escrita** — `flush_runtime_state_periodically()` do
  `apps/trader/runner.py` roda como uma task `asyncio` em background
  ao lado do loop de WebSocket, persistindo `market_state.snapshot()`
  no banco a cada `RUNTIME_STATE_FLUSH_INTERVAL_SECONDS` (2s). Um
  flush que falha é logado como `WARNING` e nunca derruba o Runner —
  o pipeline de WebSocket/agentes importa muito mais do que a
  telemetria estar perfeitamente atualizada a cada flush.
- **Lado de leitura** — `build_runtime_response()` do
  `apps/api/main.py` chama `runtime_state_repository.get()` primeiro.
  Se o Runner já deu flush pelo menos uma vez, ele reconstrói um
  `MarketState` funcional via `MarketState.from_persisted(...)` (que
  recalcula `uptime_seconds`/ratios a partir dos contadores
  persistidos, reaproveitando a lógica já existente do `snapshot()`
  em vez de duplicá-la) e monta a resposta a partir disso. Se o
  Runner nunca deu flush (ex.: a API foi iniciada isolada, sem
  nenhum Runner), ele recai no seu próprio `market_state` local para
  que o endpoint ainda retorne padrões zerados sensatos em vez de dar
  erro.

Isso é sempre uma única linha sobrescrita (`id=1`), não um histórico
crescente — é telemetria ao vivo, não um audit trail. `EquityCurve`/
`PortfolioSnapshot` já cumprem o papel de "histórico ao longo do
tempo" para dados de portfolio.

Coberto em `tests/test_market_state.py` (`TestFromPersisted`),
`tests/test_runtime_state_repository.py`, `tests/test_trader_runner.py`
(`TestFlushRuntimeStatePeriodically`) e `tests/test_api.py`
(os testes de simulação cross-process do `TestRuntimeEndpoint`) —
cada um exercitando uma instância de `MarketState` genuinamente
separada para simular o cenário real de dois processos, não apenas
fazendo assert contra o mesmo objeto que escreveu os dados.

---

# DRAWDOWN: ESCOPO DE SESSÃO

`PortfolioService.build_snapshot()` calcula o % de drawdown contra o
verdadeiro pico histórico de equity já alcançado
(`PortfolioRepository.get_max_equity()`), não apenas contra o
saldo/equity atual — do contrário o drawdown seria subestimado sempre
que o equity caísse a partir de um ponto mais alto alcançado num
snapshot anterior.

Essa busca de pico é escopada por `PortfolioSnapshot.initial_balance`:
apenas snapshots registrados sob o mesmo `account_balance` configurado
(`core/config/trading_config.py`) contam para o pico no cálculo atual.

**Por que isso importa:** sem esse escopo, resetar deliberadamente a
conta de paper trading — por exemplo, baixando `account_balance` de
100 para 10 — deixava snapshots antigos, de equity muito mais alto,
na tabela. O próprio próximo snapshot construído após o reset
calcularia algo como `(100 - 10) / 100 = 90%` de drawdown, mesmo que a
conta nunca tivesse de fato perdido nada; ela só tinha sido
reconfigurada de propósito para um saldo menor. `get_max_equity(user_id,
initial_balance=None)` (o padrão) ainda retorna o máximo histórico
sem escopo para qualquer chamador existente que não passe
`initial_balance` — só a própria chamada interna de
`PortfolioService.build_snapshot()` passa esse parâmetro, já que é o
único lugar onde essa distinção realmente importa.

Uma perda real *dentro* da mesma sessão (mesmo `initial_balance` do
início ao fim) não é afetada e continua contando normalmente.

Coberto em `tests/test_portfolio_service.py`
(`TestPeakEquitySessionScoping`).

---

# CONSOLE ENGINE

Padronização visual:

## Arquivos de log por processo

Cada processo grava em seu próprio arquivo em `logs/` — não existe
mais um único `runtime.log`/`errors.log` compartilhado:

- Launcher: `logs/runtime.log` / `logs/errors.log` (nomes sem sufixo
  -- é o processo "padrão")
- Runner: `logs/runtime-runner.log` / `logs/errors-runner.log`
- Optimizer: `logs/runtime-optimizer.log` / `logs/errors-optimizer.log`
- Backtest: `logs/runtime-backtest.log` / `logs/errors-backtest.log`

Corrige um bug real: dois processos distintos escrevendo
concorrentemente no mesmo arquivo (sem nenhum lock entre eles)
corrompe/derruba linhas silenciosamente — sem lançar exceção em
nenhum dos dois lados. Confirmado reproduzindo diretamente (dois
processos logando 300 linhas cada, concorrentemente, perderam dezenas
de linhas cada um por corrupção). Controlado pela env var
`CRYPTO_BOT_LOG_PROCESS`, setada no topo de cada entry point antes de
qualquer outro import (ver `core/utils/console_logger.py`).

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

# STARTUP / LAUNCHER

Os entrypoints (`scripts/start.ps1` no Windows, `scripts/start.sh` no
Linux/macOS) delegam ambos para o mesmo launcher interativo:

```text
scripts/bootstrap/launcher.py
```

Sequência de boot:

```text
cleanup_old_processes()      -- scripts/bootstrap/process_manager.py
        ↓
validate_environment()       -- scripts/bootstrap/validate.py
        ↓
install_requirements()       -- scripts/bootstrap/bootstrap.py
        ↓
show_menu() / runtime loop
```

## validate_environment()

Verificações realizadas:

| Check       | Bloqueante? | O que verifica                                        |
|-------------|-------------|--------------------------------------------------------|
| Python      | Sim         | Python >= 3.11                                         |
| Structure   | Sim         | `apps/`, `core/`, `data/`, `scripts/` existem           |
| Files       | Sim         | `.env` e `scripts/bootstrap/requirements.txt` existem   |
| VirtualEnv  | Não (warn)  | `.venv/` existe                                         |
| Frontend    | Não (warn)  | `frontend/` existe                                      |

`Frontend` e `VirtualEnv` são apenas informativos — sua ausência
loga um `WARNING` mas nunca falha `validate_environment()` nem
bloqueia o startup. Isso importa independentemente do estado do
frontend num checkout específico: `start_fullstack()` nunca pode
depender obrigatoriamente da existência de `frontend/`.

## Menu de runtime

```text
[1] Runner       -> python -m apps.trader.runner
[2] Optimizer    -> python -m backtest.optimizer.optimizer_engine
[3] Backtest     -> python -m backtest.runner
[4] Frontend     -> npm run dev (cwd=frontend/), somente se frontend/ existir
[5] Full Stack   -> API + Runner, mais Frontend se frontend/ existir
[0] Exit
```

## Full Stack (`[5]`)

Inicia, como processos de SO separados:

1. **API** — `uvicorn apps.api.main:app` em `http://127.0.0.1:8000`
2. **Runner** — `apps.trader.runner` (paper trading ao vivo contra o
   WebSocket de market-data da Binance)
3. **Frontend** — apenas se `frontend/` existir *e* as dependências
   npm puderem ser resolvidas/instaladas; caso contrário um warning é
   logado e o Full Stack continua rodando só com API + Runner.

`Ctrl+C` encerra todos os processos iniciados de forma limpa
(`terminate_process()` envia `SIGTERM`/terminate gracioso, depois
força kill após um timeout de 5s se um processo não sair).

### Startup do frontend, passo a passo

`start_frontend()`/`start_fullstack()` passam por três verificações
antes de subir o dev server, cada uma com seu próprio fallback que
não derruba o processo:

1. **`frontend_available()`** — `frontend/` existe? Se não:
   `warn_frontend_unavailable()`, roda só com API + Runner.
2. **`resolve_npm_command()`** — `shutil.which("npm")`. No Windows
   isso resolve para `npm.cmd` (o executável real; `npm` em si não é
   invocável diretamente via `CreateProcess` sem `shell=True`). Se o
   npm não for encontrado: `warn_npm_not_found()`, roda só com
   API + Runner.
3. **`frontend_dependencies_installed()`** — `frontend/node_modules/`
   existe? Nunca é versionado (grande, reprodutível). Se estiver
   ausente, `install_frontend_dependencies()` roda `npm install` em
   `frontend/` automaticamente, da mesma forma que
   `install_requirements()` faz no lado Python. Se essa instalação
   falhar (exit code não-zero): roda só com API + Runner.

Só depois que as três passam é que o dev server é de fato aberto via
`Popen`.

**Histórico de bugs**, para contexto sobre por que as três
verificações existem de forma independente:

- `start_fullstack()` originalmente iniciava o frontend
  incondicionalmente e quebrava com `FileNotFoundError` quando
  `frontend/` ainda não existia (check #1).
- Depois que `frontend/` foi construído,
  `subprocess.Popen(["npm", ...])` (sem `shell=True`) ainda quebrava
  no Windows especificamente com `FileNotFoundError ([WinError 2])`,
  porque o `npm` lá é `npm.cmd`, e `CreateProcess` não faz a
  resolução de `PATHEXT` que o shell faz (check #2).
- Depois desse fix, um checkout novo ainda tinha `frontend/` sem
  `node_modules/`, então `npm run dev` (que na prática é só `vite`)
  falhava com `'vite' is not recognized...` (Windows) /
  `vite: not found` (Linux) (check #3).

As três são cobertas em `tests/test_launcher.py`, cada uma isolando
`ROOT` para um diretório temporário e mockando `shutil.which`/
`subprocess.run`/`subprocess.Popen` em vez de depender de um dado
checkout/máquina de CI ter `frontend/`, `npm` ou `node_modules/` em
algum estado específico.

---

# FRONTEND

```text
frontend/
├── src/
│   ├── api/client.js          -- fetch wrapper para a API
│   ├── hooks/usePolling.js    -- polling hook usado pelas duas páginas
│   ├── lib/format.js          -- formatação de currency/percent/date
│   ├── components/            -- Panel, StatCard, Badge, TradesTable,
│   │                             PnlChart, EventLog
│   └── pages/
│       ├── Dashboard.jsx      -- página Monitor
│       └── Settings.jsx       -- página Settings
└── vite.config.js             -- fixado na porta 5173 (bate com o CORS da API)
```

React + Vite. O estado é buscado via polling (`usePolling`, intervalo
de 3s no dashboard, 15s nas settings) em vez de WebSocket — mais
simples, e a API já é uma superfície REST simples.

## Monitor (`pages/Dashboard.jsx`)

Renderiza `GET /dashboard` (runtime + metrics + portfolio + trades
abertos/fechados em uma única chamada). Equity, PnL total, drawdown,
win rate, contagem de posições abertas e expectancy como stat cards;
trades abertos e recém-fechados como tabelas; um gráfico de barras
de PnL por trade; e um detalhamento do pipeline de sinais (executado
vs. motivos de bloqueio de sinal, a partir de
`runtime.execution_reasons` / `runtime.blocked_signal_reasons`).

Mais dois painéis fazem polling dos seus próprios endpoints
separadamente (intervalo de 5s, contra 3s da chamada principal do
dashboard — mudam com menos frequência):

- **`RiskStatusBanner`** (`GET /risk-status`) — verde com a contagem
  de trades de hoje quando tudo liberado; vermelho nomeando o limite
  exato violado (`DAILY_LOSS_LIMIT_REACHED` /
  `DAILY_TRADE_LIMIT_REACHED`) quando o bot pausou por hoje. Ver
  PROTEÇÃO DE RISCO DIÁRIA.
- **`AdvancedMetricsPanel`** (`GET /metrics/advanced`) — Sharpe,
  Sortino, max drawdown histórico, profit factor e sequências de
  vitórias/derrotas atual/melhor. Ver ANÁLISE AVANÇADA DE TRADES.

## Settings (`pages/Settings.jsx`)

Quatro painéis, todos salvando via `PUT /settings` (campos opcionais
— só o que mudou é enviado) e disparando `handleSaved` (que dá
`refresh()` e emite o evento `window` `crypto-bot-settings-updated`,
escutado por `Tools.jsx` para recarregar seus próprios settings):

- **Modo de execução (`ModePanel`)** — três opções: **Paper**
  (padrão, sem risco), **Live Testnet** e **Live Mainnet** (ordens
  reais, marcado com badge de perigo). As duas opções Live ficam
  bloqueadas (`Badge "Bloqueado"`) até `settings.live_trading_available`
  vir `true` da API — que só acontece com credenciais configuradas
  E `live_trading_confirmed=true` (ver Settings API abaixo). Trocar
  de modo abre um modal de confirmação (`ModeConfirmModal`) antes de
  enviar `PUT /settings`; a API já bloqueia a troca com posição
  aberta (409 — ver `Bloqueação de troca de modo com posição aberta`
  no LIVE TRADING abaixo).
- **Credenciais da carteira (`CredentialsPanel`)** — key/secret da
  Binance (Testnet ou mainnet, conforme o modo ativo). Credenciais já
  configuradas são exibidas como uma máscara de tamanho fixo
  (`binance_api_key_masked`); o valor real nunca é reenviado pela API
  depois de salvo. Um botão "Limpar" por campo é a única forma de
  remover uma chave salva. Em modo `live`, mostra o saldo real da
  conta (`GET /account/live-balance`, atualizado a cada 30s); em modo
  `paper`, o saldo é editável manualmente.
- **Pares monitorados e mercado (`PairsPanel` + `MarketFields`)** —
  grade de pares para ativar/desativar (validada contra a API pública
  da Binance direto do browser, `GET api.binance.com/.../exchangeInfo`
  — não passa pelo backend, então não é afetada pelo CORS restrito de
  `apps/api/main.py`) e o timeframe dos candles. Ambos requerem
  restart do bot para valer.
- **Formulário unificado de parâmetros (`AllParamsForm`)** — todos os
  demais parâmetros (risco, limites diários, ATR, qualidade de sinal,
  estrutura de mercado, gestão de posição, precisão de exchange,
  simulação) num único formulário com um único botão salvar, gerado
  declarativamente a partir do array `GROUPS`. Cada campo tem um
  tooltip com hint (hover no label, delay de 400ms).

## Ferramentas (`pages/Tools.jsx`)

Terceira página do frontend (não documentada anteriormente no README
raiz) — roda o **Optimizer** e o **Backtest** direto pela interface,
sem precisar do terminal:

- Botões para disparar `POST /jobs/optimizer` (com seletor de janela
  de dias: 30/60/90) ou `POST /jobs/backtest`, bloqueados enquanto o
  Runner estiver ativo (job e bot nunca rodam ao mesmo tempo).
- Progresso em tempo real via polling de `GET /jobs/status` +
  `GET /jobs/progress` (intervalo de 1.5s enquanto um job está
  rodando, 5s em repouso).
- Estimativa de duração antes de rodar (`GET /jobs/estimate`) —
  heurística baseada em execuções anteriores do mesmo tipo/janela,
  guardadas em `backtest/reports/jobs_history.json`.
- Histórico paginado dos últimos jobs (`GET /jobs/history`), com
  resumo de resultado por item (winrate, PnL, profit factor para
  backtest; melhores parâmetros + score para optimizer).
- Preview antes de aplicar a melhor configuração encontrada pelo
  Optimizer (`GET /jobs/preview-apply`, mostra config atual vs. nova
  lado a lado) e confirmação explícita (`POST /jobs/apply`).
- Botão "Forçar reset" (`POST /jobs/reset`) que aparece só quando o
  estado interno do job trava (`_current_job["status"] == "running"`
  mas a thread já morreu) — usa `get_open_orders`-style auto-detecção
  no backend antes de expor a opção.

## Testes automatizados do frontend

```bash
cd frontend
npm test        # roda uma vez (vitest run)
npm run test:watch   # modo watch, para desenvolvimento
```

Vitest + Testing Library (`@testing-library/react`,
`@testing-library/user-event`, `jsdom`), configurado em
`vite.config.js` (bloco `test:`) reutilizando o mesmo setup do Vite —
sem arquivo de config separado. `src/setupTests.js` carrega os
matchers do `@testing-library/jest-dom`.

Cobertura atual:

- `src/api/client.test.js` — o wrapper `request()` (sucesso, erro de
  rede vira `ApiError` com `status=0`, erro HTTP usa `detail` do
  corpo da resposta, fallback para mensagem genérica sem corpo JSON,
  `204` retorna `null`) e a construção de query string/método/corpo
  de alguns endpoints representativos.
- `src/hooks/usePolling.test.js` — estado de loading inicial, dado
  populado após o primeiro fetch, erro não limpa dado anterior
  (stale-but-visible), `refresh()` dispara fetch imediato, polling
  para após unmount.
- `src/pages/Dashboard.test.jsx` — loading state, render dos dados
  do portfolio após resolver, error state quando a API está
  inacessível, badge de feed de mercado conectado/desconectado.
  `api` é mockado via `vi.mock` — nenhum destes testes faz rede real.
- `src/pages/Settings.test.jsx` — loading/error state, render dos
  quatro painéis, bloqueio dos modos Live sem
  `live_trading_available`, fluxo completo de troca de modo
  (clique → modal de confirmação → `PUT /settings`), e edição de um
  parâmetro no formulário unificado até o payload salvo (valores
  `int`/`float` são convertidos antes do envio, testado
  explicitamente). `PairsPanel`'s `fetch` direto à Binance é mockado
  para falhar rápido e cair no fallback local (`DEFAULT_PAIRS`), já
  que não há rede disponível no ambiente de teste.

## Settings API (`core/config/settings_repository.py`)

Lê/escreve diretamente no `.env` real, preservando comentários,
linhas em branco e ordem das chaves (um dump ingênuo de `os.environ`
destruiria tudo isso). Pontos-chave:

- `mode` aceita `"paper"` ou `"live"`. Trocar para `"live"` aqui
  **não**, por si só, habilita ordens reais na mainnet — ver LIVE
  TRADING abaixo para a trava separada e deliberada que faz isso.
- API key/secret precisam ter exatamente 64 caracteres (formato da
  Binance) ou string vazia para limpar.
- `GET /settings` nunca retorna os valores reais de key/secret, só
  `*_set: bool` e uma máscara fixa `••••••••`.
- `live_trading_available` é `true` apenas quando AMBAS as
  credenciais da Binance estão definidas E `LIVE_TRADING_CONFIRMED=true`
  está setado no `.env` — nenhuma das duas sozinha é suficiente,
  espelhando a própria trava do `BinanceTradingClient`.

## LIVE TRADING

Execução real de ordens contra a Binance, de ponta a ponta: uma
entrada MARKET BUY, uma OCO protetora (stop loss + take profit)
colocada imediatamente depois, e um restart automático do Runner ao
trocar de modo pelo painel Settings.

```text
core/services/binance_trading_client.py    -- cliente REST autenticado
core/services/execution_router.py          -- ponto de decisão paper vs. live
core/services/process_manager_service.py    -- reinicia o processo Runner
core/utils/runner_pid.py                    -- ponte de PID file API <-> Runner
apps/api/main.py                            -- PUT /settings: bloqueio + restart
frontend/src/pages/Settings.jsx             -- seletor de modo + modal de confirmação
```

### Por que um restart é necessário para trocar de modo

`MODE` / `BINANCE_TESTNET` / `LIVE_TRADING_CONFIRMED` de
`core/config/settings.py` são lidos uma única vez, no momento do
import do Python. Um processo Runner em execução mantém os valores
com que iniciou, independente do que for escrito no `.env` depois —
não existe mecanismo in-process para fazê-lo captar um `MODE`
alterado. Reiniciar o processo é o que recarrega `settings.py` a
partir do `.env` atualizado. `PUT /settings` dispara isso
automaticamente (só quando `mode` está de fato presente no request —
atualizar apenas credenciais ou `binance_testnet` não reinicia nada,
já que `execution_router.py` relê as settings do zero a cada chamada
de `execute()` em vez de fazer cache delas).

### A trava de segurança da mainnet

Chegar à mainnet (fundos reais) exige **ambos**:
1. `BINANCE_TESTNET=false`
2. `LIVE_TRADING_CONFIRMED=true`

Essas condições são deliberadamente separadas entre si e do `MODE`.
Uma pessoa poderia setar `MODE=live` e `BINANCE_TESTNET=false` numa
única edição do `.env` achando que estava configurando outra coisa —
essa única edição nunca pode ser suficiente para habilitar colocação
de ordens com dinheiro real. `LIVE_TRADING_CONFIRMED` precisa ser
setado como seu próprio passo explícito. `BinanceTradingClient.__init__`
lança `MainnetNotConfirmedError` se solicitado a mirar a mainnet sem
isso — aplicado de novo no momento da construção, não só por quem
quer que o tenha chamado, caso um bug futuro na própria verificação
de `execution_router.py` seja algum dia introduzido.

### Sequência de execução ao vivo

1. **Entrada MARKET BUY.** Se falhar, nada aconteceu ainda — o sinal
   é rejeitado exatamente como uma falha de validação.
2. O **preço médio de fill real** é calculado a partir da resposta da
   ordem (`cummulativeQuoteQty / executedQty`), nunca o preço que o
   sinal pediu — uma ordem MARKET preenche pelo que o order book
   oferecer. Todo preço downstream (stop loss, take profit) é
   recalculado em relação a esse fill real, preservando a
   *distância de risco original* que o RiskAgent calculou no momento
   do sinal.
3. A **OCO protetora** (take profit + stop loss juntos, via
   `POST /api/v3/orderList/oco` — o endpoint atual, não deprecated)
   é colocada usando esse preço de fill real.
4. Só depois que **ambas** as ordens têm sucesso é que algo é escrito
   na tabela local `trades`.

### O modo de falha mais perigoso, e como é tratado

Se a entrada tem sucesso mas a OCO falha, a conta agora detém uma
**posição real e desprotegida** — sem stop loss, sem take profit,
exposição total ao que o mercado fizer a seguir. Isso é tratado como
pior que qualquer outra falha que esse código possa produzir,
incluindo uma entrada totalmente falha, porque dinheiro real já está
na mesa sem rede de segurança.

A resposta é um **market SELL** imediato pela mesma quantidade,
aceitando qualquer slippage que isso custe — uma perda pequena e
conhecida, imediata, é um resultado muito melhor do que uma posição
desprotegida ficar aberta até um humano perceber. Se esse fechamento
de emergência *também* falhar, isso é logado em nível `ERROR` com
uma mensagem inequívoca ("MANUAL INTERVENTION REQUIRED IMMEDIATELY")
e um `ExecutionResult.reason` distinto
(`LIVE_POSITION_UNPROTECTED_MANUAL_ACTION_REQUIRED`) — não há mais
nenhum recurso automatizado a partir desse ponto, e a falha nunca
pode ficar silenciosamente indistinguível de uma que foi tratada com
sucesso.

Coberto em `tests/test_execution_router.py`
(`TestUnprotectedPositionHandling`, incluindo o cenário de pior caso
de falha dupla) e `tests/test_binance_trading_client.py`.

### Bloqueio de troca de modo com posição aberta

`PUT /settings` retorna `409` se existir qualquer posição real
(`Trade.status == "OPEN"`) quando `mode` está no payload do request —
reiniciar o Runner com uma posição aberta deixaria o lifecycle dessa
posição sem gerenciamento (nenhum agente observando seu stop
loss/take profit) por todo o tempo que o restart levar. Isso é um
bloqueio duro, não um aviso; a pessoa precisa fechar a posição
primeiro. Atualizações que não tocam em `mode` nunca são bloqueadas
por essa verificação, mesmo com uma posição aberta.

### Reconciliação de startup (`core/services/startup_reconciler.py`)

Antes do Runner começar a operar em `MODE=live`
(`apps/trader/runner.py`, chamado logo depois de carregar os filtros
de símbolo), o estado real da Binance é comparado com o banco local.
Três cenários são cobertos:

1. **Trade `OPEN` no banco, OCO já `ALL_DONE` na Binance.** A posição
   fechou enquanto o bot estava offline — marcada como `CLOSED` com
   `exit_reason=RECONCILED_CLOSED`.
2. **Trade `OPEN` no banco, mas a Binance confirma que a OCO não
   existe** (código `-2013`, "Order does not exist"). Só nesse caso —
   erro específico, não qualquer exceção — é seguro assumir que a
   posição ficou desprotegida: um market SELL de emergência é
   disparado e o trade é fechado com
   `exit_reason=RECONCILED_EMERGENCY_CLOSE`. Qualquer outro erro
   (rede, timeout, auth) só loga `CRITICAL` — o estado real é
   desconhecido, e fechar automaticamente nesse caso arrisca cancelar
   uma proteção que na verdade ainda existe.
3. **Ordem/OCO aberta na Binance sem nenhum trade `OPEN`
   correspondente no banco local** (posição aberta fora do bot, ou
   banco apagado/perdido). Loga `CRITICAL` por símbolo configurado —
   nunca cancela nem fecha nada automaticamente, já que agir sobre um
   estado desconhecido é mais arriscado que alertar o operador.

Trades sem `order_list_id` (criados antes do rastreamento de ordens
existir) não podem ser verificados contra a Binance e também logam
`CRITICAL`. Todo ponto `CRITICAL` aqui é o gancho para o alerta
externo via webhook (`WEBHOOK_ALERT_URL`, roadmap da Fase 2) — por
ora, esses pontos só logam localmente em `logs/errors.log`.

Coberto por `tests/test_startup_reconciler.py` com mocks (sem acesso
de rede real neste ambiente de dev — confirmado em
`tests/test_binance_trading_client.py`).

#### Checklist de validação manual contra a Binance Testnet

A suíte de testes só cobre respostas mockadas. Antes de confiar nessa
reconciliação com dinheiro real, valide manualmente contra a Testnet
(`BINANCE_TESTNET=true`, chaves de API da própria Testnet, nunca de
mainnet):

1. **Cenário 1 (OCO já resolvida).** Abra uma posição pelo Runner em
   `MODE=live` + testnet, deixe a OCO ser preenchida manualmente pela
   UI da Testnet (ou aguarde o preço cruzar o take profit/stop loss),
   pare o Runner, reinicie-o e confirme no console/`logs/runtime-runner.log`
   a mensagem `OCO já resolvida — marcando como fechada` e que o
   trade aparece `CLOSED` com `RECONCILED_CLOSED` no banco.
2. **Cenário 2 (OCO sumiu).** Abra uma posição, pare o Runner, cancele
   manualmente a OCO pela UI/API da Testnet, reinicie o Runner e
   confirme a mensagem de fechamento de emergência e que uma ordem
   MARKET SELL real aparece no histórico da Testnet.
3. **Cenário 2 — erro genérico.** Repita o passo anterior mas, antes
   de reiniciar o Runner, derrube a conectividade de rede
   momentaneamente (ou use uma API key temporariamente inválida) para
   forçar um erro diferente de `-2013` na consulta — confirme que o
   log mostra `CRITICAL`/"estado real desconhecido" e que **nenhuma**
   ordem de venda é disparada.
4. **Cenário 3 (ordem órfã).** Com o Runner parado e sem nenhum trade
   `OPEN` no banco, abra uma ordem/OCO manualmente pela UI da Testnet
   para um dos símbolos configurados em `SYMBOLS`, inicie o Runner e
   confirme a mensagem `CRITICAL` de ordem órfã no log, e que nenhuma
   ordem foi cancelada.
5. Em todos os casos, confirme que o Runner segue operando
   normalmente depois da reconciliação (nenhuma exceção não tratada
   interrompe o startup).

### O bug do processo zumbi (encontrado e corrigido durante a construção disso)

Confirmado empiricamente: quando o processo da API inicia o Runner
via `subprocess.Popen` e manda `SIGTERM`, o filho vira um zumbi até
que algo chame `Popen.wait()`/`.poll()` nele — `os.kill(pid, 0)` e
`ps -p <pid>` **ambos** continuam reportando o zumbi como "vivo"
indefinidamente, já que nada mais está posicionado para dar reap num
filho daquele processo específico. `Popen.poll()` retornou `-15`
(terminado, confirmado) no exato mesmo momento real em que `ps -p`
ainda listava o processo como rodando.

`process_manager_service.py` mantém um handle em memória
(`_managed_process`) de qualquer Runner que ele mesmo tenha iniciado,
e prefere `Popen.wait()`/`.poll()` para liveness/terminação sempre
que esse handle existe — caindo de volta em
`os.kill(pid, 0)`/`tasklist` só quando não existe (ex.: um Runner
iniciado pelo terminal original do launcher, não pela API). Antes
desse fix, reiniciar levava 10-15+ segundos (a cadeia completa de
timeout graceful-depois-force-kill, toda vez) porque o zumbi nunca
era detectado como morto; depois do fix completa em bem menos de um
segundo.

Coberto em `tests/test_process_manager_service.py`
(`TestZombieProcessHandling`), usando um subprocesso real em vez de
um mock, já que o bug é especificamente sobre semântica de
processo/signal em nível de SO que um mock encobriria.

### O que ainda é manual

Nada em termos de *alertar* existe ainda além do log de console — o
caso `MANUAL INTERVENTION REQUIRED` acima é tão alto quanto quem
estiver olhando o terminal/arquivo de log naquele momento. Um alerta
externo (email, SMS, webhook) para esse caminho de falha específico
é uma próxima adição razoável, ainda não construída.

---

# TESTES

```bash
pip install -r scripts/bootstrap/requirements.txt pytest pytest-asyncio pytest-cov
python -m pytest tests/
```

Relatório de coverage:

```bash
python -m pytest tests/ --cov=core --cov=data --cov=backtest --cov=apps --cov-report=term-missing
```

`tests/conftest.py` fornece duas fixtures autouse, com escopo de
sessão:

- **Banco isolado** — redireciona o engine e o `SessionLocal` de
  `data.storage.database` para um arquivo SQLite temporário durante
  toda a sessão de testes, e trunca tabelas entre testes. O
  `data/storage/trades.db` real nunca é lido nem escrito pela suíte.
- **Logs isolados** — redireciona os file handlers de
  `runtime_logger`/`error_logger` para um diretório temporário. Os
  `logs/runtime.log` e `logs/errors.log` reais nunca são escritos
  pela suíte.

A cobertura abrange: EventBus, todos os repositories, todos os
serviços analíticos (ATR, EMA trend, market structure, market regime,
signal quality), o pipeline completo de agentes (sinal → risco →
execução → saída), o backtest engine e o optimizer, o validation
interpreter, o dashboard FastAPI, as migrations do alembic contra um
banco novo, e os scripts de bootstrap/launcher.

---

# ESTRUTURA DO PROJETO

```text
apps/
core/
data/
backtest/
frontend/
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

# ANÁLISE AVANÇADA DE TRADES

`core/services/trade_analytics.py` contém funções puras, sem I/O,
sobre uma lista de PnLs de trades (equity curve, max drawdown,
sequências de vitórias/derrotas, profit factor, risk/reward, recovery
factor, Sharpe, Sortino). Extraído de
`backtest/engine/metrics_engine.py`, que originalmente calculava isso
só para backtests, para que live trading e backtesting compartilhem
uma única implementação em vez de duas que poderiam divergir
silenciosamente.

```text
core/services/trade_analytics.py        -- funções puras
core/services/trade_metrics_service.py  -- get_advanced_metrics() (live)
backtest/engine/metrics_engine.py       -- generate() (backtest)
```

**Bug corrigido durante a extração:** a implementação original do
backtest iterava `trades_repository.get_closed_trades()` diretamente,
que ordena os resultados `DESC` por `closed_at` (mais recente
primeiro). O loop de equity-curve/streak precisa de ordem cronológica
(mais antigo primeiro) — `metrics_engine.py` agora inverte
explicitamente a lista de trades antes de passá-la para
`compute_equity_curve_stats()`.

## Convenção de Sharpe / Sortino

Ambos tratam o PnL de cada trade como uma observação de "retorno".
Não existe uma taxa livre de risco natural por trade para um bot
paper intraday, então ambos usam a forma simplificada, sem taxa
livre de risco, comum na avaliação de estratégias de varejo:
retorno médio ÷ desvio (downside) dos retornos. Isso serve para
comparar a consistência trade a trade do próprio bot ao longo do
tempo, não como substituto de um benchmark de risco livre em nível de
instrumento. Sortino só penaliza o desvio de downside — uma sequência
com um grande outlier de alta pontua significativamente mais alto do
que uma com um outlier de baixa igualmente grande, mesmo com médias
idênticas (ver `tests/test_trade_analytics.py::TestComputeSortinoRatio::
test_only_penalizes_downside_not_upside_volatility`).

## `max_drawdown` aqui vs. `PortfolioResponse.drawdown`

Esses são números deliberadamente diferentes:

- `trade_analytics.compute_equity_curve_stats()["max_drawdown"]` — a
  verdadeira queda histórica de pico a vale em **todo trade fechado
  já existente**, em dólares. Usado por `GET /metrics/advanced` e o
  relatório de backtest.
- Drawdown escopado por sessão do `PortfolioService` (ver DRAWDOWN:
  ESCOPO DE SESSÃO) — um percentual medido contra o pico de equity
  alcançado sob a **configuração atual de account-balance**. Usado
  para o stat principal de drawdown do dashboard ao vivo e os circuit
  breakers diário/de sessão.

## API / Frontend

`GET /metrics/advanced`
(`apps/api/schemas/advanced_metrics_schema.py`) expõe
`TradeMetricsService.get_advanced_metrics()` para o
`AdvancedMetricsPanel` do dashboard (Sharpe, Sortino, max drawdown,
profit factor, sequências de vitórias/derrotas atual/melhor).

Coberto em `tests/test_trade_analytics.py`,
`tests/test_backtest_engine.py` (cobertura de regressão do refactor)
e `tests/test_api.py` (`TestAdvancedMetricsEndpoint`).

---

# OPTIMIZER & BACKTEST: DADOS HISTÓRICOS REAIS

O `OptimizerEngine` de `backtest/optimizer/optimizer_engine.py`
costumava ajustar parâmetros contra os mesmos CSVs sintéticos,
pequenos e fixos, em `backtest/datasets/` a cada execução,
independentemente de como o mercado real havia se movido desde então
(esses arquivos: ~20 candles cada, última modificação em 2026-05-07,
mais um `validation.csv` de 500 linhas). Agora ele busca histórico
real da Binance pelo endpoint público de klines antes de cada
execução.

```text
data/ingestion/binance_history.py   -- fetch/paginate/split/write
backtest/optimizer/optimizer_engine.py
                                     -- __init__/_prepare_datasets,
                                        BLOCKING_VERDICTS gate
```

## Fetch

`OptimizerEngine.HISTORY_DAYS` (90) dias de candles no intervalo de
`KLINE_INTERVAL` por `SYMBOLS` configurado, via o endpoint *público*
e não autenticado `/api/v3/klines` — dados de mercado somente
leitura, do mesmo tipo de informação pública que o feed de WebSocket
de `data/ingestion/binance_ws.py` já lê, não um endpoint autenticado
de trading. Pagina (a Binance retorna no máximo 1000 candles/chamada),
tenta de novo em caso de `429` respeitando o `Retry-After`, e tenta
de novo erros de rede transitórios com backoff exponencial.

**Recai nos datasets sintéticos** (com um `WARNING` claro no log,
nunca um crash) se o fetch falhar por qualquer motivo — um soluço de
rede nunca pode bloquear a execução de uma otimização por completo,
deve só usar dados mais fracos de forma visível.

## Split de treino/validação

`OptimizerEngine.VALIDATION_DAYS` (15) dos candles **mais recentes**
são reservados para validação; tudo mais antigo é dado de treino.
Isso é um **split temporal, não aleatório**
(`data.ingestion.binance_history.split_train_validation`) — embaralhar
candles antes de dividir permitiria que o optimizer "validasse"
contra dados cronologicamente intercalados com o que treinou, o que é
data leakage: faria um conjunto de parâmetros overfit parecer
validado quando nunca foi de fato testado contra dados não vistos.

## Gate de validação

**Bug corrigido:** `core/config/best_config.json` era escrito
**incondicionalmente**, *antes* mesmo da validação walk-forward
rodar. Um conjunto de parâmetros que o próprio relatório de validação
do optimizer marcava como overfit (`PROMISING_BUT_SUSPICIOUS`) ou
baseado em dados insuficientes (`INSUFFICIENT_DATA`) ainda era
captado por `core/config/config_loader.py` no próximo start do
Runner, exatamente como se tivesse passado na validação de forma
limpa.

Corrigido: o save agora acontece *depois* que o veredito walk-forward
é conhecido, e é pulado por completo
(`OptimizerEngine.BLOCKING_VERDICTS`) para `PROMISING_BUT_SUSPICIOUS`
e `INSUFFICIENT_DATA`. `ROBUST` e `MODERATE` ainda salvam normalmente.
Um save bloqueado deixa qualquer `best_config.json` já existente
completamente intocado, logando um `WARNING` explicando o motivo.

Coberto em `tests/test_binance_history.py` e
`tests/test_optimizer_engine.py` (`TestPrepareDatasetsFallback`,
`TestPrepareDatasetsSuccess`, `TestValidationGate`).

## Backtest (`backtest/runner.py`)

`backtest/runner.py` (opção de menu `[3]`) é um entrypoint
**separado** do optimizer — ele avalia a estratégia atualmente
configurada contra o histórico, em vez de ajustar parâmetros, então
originalmente tinha sua própria lista `DATASETS` hardcoded apontando
para os mesmos CSVs sintéticos, completamente desconectada do fetch
de dados reais do optimizer.

**Bug corrigido:** rodar o optimizer primeiro captava o histórico
real da Binance (como projetado), mas rodar o Backtest depois ainda
usava silenciosamente os datasets sintéticos antigos — os dois
entrypoints nunca estiveram de fato conectados, então corrigir um não
corrigia o outro.

O Backtest agora chama seu próprio `prepare_datasets()` (espelhando
`OptimizerEngine._prepare_datasets()`), buscando `HISTORY_DAYS` (90)
dias de histórico real por símbolo com o mesmo comportamento de
fallback para sintético em caso de falha. Sem split de
treino/validação aqui, ao contrário do optimizer — o Backtest está
avaliando a estratégia atual contra o histórico real, não
selecionando parâmetros, então não há o risco de "validar contra os
mesmos dados que treinou" a se prevenir.

**Segundo bug corrigido durante essa integração:** a primeira versão
de `prepare_datasets()` chamava `asyncio.run()` internamente, mas é
invocada de dentro de `main()` — que já é uma função `async` rodando
dentro do seu próprio `asyncio.run(main())` no entrypoint real
(`if __name__ == "__main__": asyncio.run(main())`). Chamar
`asyncio.run()` de novo a partir de um event loop já em execução
lança `RuntimeError: asyncio.run() cannot be called from a running
event loop` — que o próprio `except Exception` de `prepare_datasets()`
capturava e engolia silenciosamente. O efeito prático: toda execução
real caía de volta nos datasets sintéticos incondicionalmente,
independente da disponibilidade de rede, porque o fetch real nunca
conseguia de fato *rodar*, não porque falhava. Corrigido tornando
`prepare_datasets()` em si `async` e dando `await` nela diretamente a
partir de `main()`, sem nenhum `asyncio.run()` aninhado em nenhum
ponto da cadeia de chamadas.

Os arquivos de saída usam um sufixo `_backtest.csv`
(`backtest/datasets/live_history/{symbol}_backtest.csv`), distinto
dos `_train.csv`/`_validation.csv` do optimizer no mesmo diretório
compartilhado — sem colisão de nome de arquivo entre os fetches dos
dois entrypoints.

Coberto em `tests/test_backtest_runner.py`
(`TestPrepareDatasets`, incluindo
`test_does_not_raise_runtime_error_when_called_from_a_running_loop`,
o teste de regressão especificamente para o bug de aninhamento do
asyncio).

---

# PERSISTENCE LAYER (`data/storage/database.py`)

## `PRAGMA busy_timeout`

Além dos PRAGMAs já existentes (`journal_mode=WAL`,
`synchronous=NORMAL`, `temp_store=MEMORY`, `foreign_keys=ON`),
`busy_timeout=5000` (5s) foi adicionado ao mesmo listener de conexão.
A API e o Runner são dois processos do SO separados escrevendo no
mesmo `trades.db` — WAL já permite leitores concorrentes junto com um
único escritor, mas duas escritas quase simultâneas ainda podem
colidir por uma fração de segundo. Sem `busy_timeout`, essa colisão
falha imediatamente com `database is locked`; com ele, SQLite tenta
de novo por até 5s antes de desistir. Coberto por
`tests/test_database_init.py::TestSqlitePragmaListener`.

## Backup (`scripts/backup_db.py`)

```bash
python scripts/backup_db.py [--keep N]
```

Cria uma cópia timestamped de `data/storage/trades.db` em
`data/storage/backups/` (ambos ignorados pelo git — mesma regra que
já cobre `*.db`) e remove os backups mais antigos além do limite
`--keep` (padrão: 10). Usa a própria API de backup do `sqlite3`
(`Connection.backup()`) em vez de uma cópia de arquivo simples —
como o banco roda em modo WAL, copiar só o `.db` pelo sistema de
arquivos pode perder escritas ainda pendentes no `.db-wal` e gerar um
snapshot inconsistente; a API de backup fala diretamente com o SQLite
e sempre produz uma cópia completa e consistente, sem precisar parar
a API/Runner primeiro.

Não há agendador embutido no projeto — para rodar periodicamente, use
o agendador do próprio SO (`cron` no Linux/macOS, Agendador de
Tarefas no Windows) apontando para esse comando. Coberto por
`tests/test_backup_db.py`.

## PostgreSQL

Permanece fora do escopo do roadmap atual (ver `ROADMAP ATUAL`
abaixo) — SQLite com WAL + `busy_timeout` é considerado suficiente
para o volume de escrita atual (um único bot por instância, poucas
escritas por segundo mesmo em picos de sinal).

---

# PRODUCTION HARDENING (`apps/api/main.py`, `apps/trader/runner.py`)

## Autenticação de API (`X-API-Token`)

`PUT /settings`, `POST /runner/start` e `POST /runner/stop` — os
únicos endpoints capazes de mudar configuração ou controlar o ciclo
de vida do bot — exigem o header `X-API-Token` batendo com
`API_ACCESS_TOKEN` (`.env`) quando essa variável está definida.
Vazia/não definida (o padrão, coerente com o design original
localhost-only desta API) desabilita a autenticação inteiramente.
`GET /health` e os demais endpoints de leitura permanecem sem
autenticação — são consultados com frequência pelo frontend e não
mudam estado algum. Um `WARNING` é logado no startup da API se
`API_HOST` não for localhost e `API_ACCESS_TOKEN` estiver vazio.

Implementado via `Depends(require_api_token)` (dependency do
FastAPI) nos três endpoints — ver `apps/api/main.py`. Coberto por
`tests/test_api.py::TestApiTokenAuth`.

## Rate limiting (`slowapi`)

Os mesmos três endpoints sensíveis têm limite de requisições
configurável via `API_RATE_LIMIT` (`.env`, padrão `10/minute`) —
protege contra flood acidental (ex. um script client com bug em
loop) mesmo com autenticação habilitada. Endpoints de leitura, que o
frontend consulta a cada poucos segundos, não têm limite.

## Handler global de exceção não tratada

Um `@app.exception_handler(Exception)` em `apps/api/main.py` garante
que qualquer erro não tratado dentro de uma rota vira um `500`
genérico para o cliente (sem vazar stack trace) e, antes disso, é
logado em nível `CRITICAL` com o método/path da requisição — sem
esse handler, o FastAPI já devolve 500 por padrão, mas de forma
totalmente silenciosa nos logs.

## Graceful shutdown (`SIGTERM` / `SIGINT`)

`apps/trader/runner.py` instala handlers explícitos para `SIGTERM` e
`SIGINT` (além do `KeyboardInterrupt` que `asyncio.run()` já convertia
automaticamente a partir de um `Ctrl+C`) que cancelam a task principal
de forma cooperativa, passando pelo mesmo `finally` que cancela a
flush task de runtime state e grava um flush final
(`websocket_connected=False`) antes de sair — sem isso, o `/runtime`
da API podia continuar reportando `websocket_connected=True` por até
`RUNTIME_STATE_FLUSH_INTERVAL_SECONDS` depois do processo já ter
parado. `loop.add_signal_handler` é usado quando disponível
(POSIX); no Windows (`NotImplementedError`), cai para
`signal.signal()` como fallback.

## Alerta externo via webhook (`core/services/alert_service.py`)

`WEBHOOK_ALERT_URL` (`.env`) configura um endpoint genérico que
recebe um `POST` (JSON: `level`, `message`, `context`, `timestamp`)
toda vez que um evento `CRITICAL` acontece — hoje isso cobre a
posição desprotegida sem fechamento de emergência bem-sucedido
(`core/services/execution_router.py`,
`LIVE_POSITION_UNPROTECTED_MANUAL_ACTION_REQUIRED`) e os três pontos
`CRITICAL` da reconciliação de startup (ver `LIVE TRADING` acima).
Vazio/não definido desabilita o webhook — o evento continua sendo
logado localmente (`logs/errors.log`) de qualquer forma. Chamada é
best-effort e nunca lança: uma falha ao entregar o webhook (rede,
DNS, URL inválida) nunca interfere no fluxo que já tratou o evento
CRITICAL em si.

## Código morto removido

`core/orchestrator/orchestrator.py` — um stub de scaffolding inicial,
já documentado no próprio código como não usado em lugar nenhum e
superado pelo pipeline multi-agent baseado em `EventBus` — foi
removido nesta fase, junto com um bloco de código morto e inalcançável
dentro de `apps/api/main.py` (`jobs_preview_apply`, sobra de uma
duplicação de `jobs_status`).

---

# DEPLOY (Docker)

`Dockerfile` multi-stage (frontend Node → nginx; backend Python,
usado tanto pela API quanto pelo Runner via `command:` diferente no
Compose) + `docker-compose.yml` orquestrando os três serviços. Guia
completo — variáveis específicas do Docker
(`VITE_API_BASE_URL`, `CORS_ALLOWED_ORIGINS`), segurança antes de
expor além de localhost, a divergência entre o Runner gerenciado pelo
Compose vs. pelo botão ▶ do frontend, e backup do banco dentro de um
container — em [`docs/DEPLOYMENT.md`](DEPLOYMENT.md).

Testado manualmente de ponta a ponta: build das três imagens, os três
containers saudáveis, Runner conectando de verdade ao WebSocket da
Binance, CORS liberando a origem do frontend, e `PUT /settings`
persistindo no `.env` do host via bind mount (sobrevive a
`docker compose down && up` — sem esse bind mount, escritas do painel
Settings cairiam na camada efêmera do container e seriam perdidas).

---

# ROADMAP ATUAL

## Fases concluídas

Roadmap de 6 fases para elevar a maturidade do projeto depois da
limpeza de segurança que o tornou público, da maior para a menor
exposição a risco financeiro/segurança:

1. **Exchange Integration** — reconciliação de startup (3 cenários),
   fechamento de emergência restrito ao erro `-2013` confirmado.
2. **Production Hardening** — auth por token, rate limiting, handler
   global de exceção, shutdown gracioso, alerta via webhook.
3. **Persistence Layer** — `PRAGMA busy_timeout`, backup com rotação.
4. **Frontend** — documentação de `Tools.jsx`, testes automatizados
   (Vitest + Testing Library).
5. **Docker / Deploy** — `Dockerfile` multi-stage + `docker-compose.yml`.
6. **Atualização do `CURRENT STATUS`** — este documento, refletindo o
   trabalho das 5 fases anteriores.

Detalhe completo de cada uma nas seções correspondentes acima (`LIVE
TRADING`, `PRODUCTION HARDENING`, `PERSISTENCE LAYER`, `Testes
automatizados do frontend`, `DEPLOY (Docker)`) e em `CURRENT STATUS`.

## Próximos módulos

- Validação manual contra a Binance Testnet real (ver checklist em
  `LIVE TRADING` acima) — o maior gap restante, fora do alcance deste
  ambiente de desenvolvimento.
- PostgreSQL
- Redis streams
- distributed locking
- retry engine
- AI signal optimization

---

# REGRAS IMPORTANTES

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
Persistence Layer ............. 90%
Exchange Integration .......... 78%
Risk & Analytics ............... 85%
Production Hardening .......... 92%
Frontend ....................... 75%
Deploy (Docker) ................ 90%

TOTAL: ~88%
```

Um roadmap de 6 fases (ver `ROADMAP ATUAL` abaixo, seção "Fases
concluídas") fechou a maior parte das lacunas concretas que sustentavam
os números anteriores. Por módulo:

**`Exchange Integration`** (50% → 78%) — dos três gaps concretos
listados na versão anterior deste documento, dois foram fechados:

1. ~~Sem rate-limit handling em `binance_trading_client.py`~~ — na
   verdade já existia (`_request()`, `MAX_RATE_LIMIT_RETRIES=3`,
   testado em `TestRateLimitRetry`); esta nota estava desatualizada,
   não o código.
2. ~~Sem reconciliação de startup~~ — implementada em
   `core/services/startup_reconciler.py`: posição fechada enquanto o
   bot estava offline, OCO confirmadamente sumida (só `-2013`
   aciona fechamento de emergência automático — qualquer outro erro
   apenas alerta), ordens órfãs na Binance sem trade local
   correspondente, e trades legados sem `order_list_id`. Ver `LIVE
   TRADING` acima para o detalhe completo e `tests/test_startup_reconciler.py`
   para a cobertura.
3. **Ainda em aberto: zero validação contra a API real da Binance**,
   nem mesmo testnet — este ambiente de desenvolvimento não tem
   acesso de rede a `api.binance.com` nem a `testnet.binance.vision`.
   Todo teste mocka a camada HTTP. Um checklist de validação manual
   (testnet, chaves reais de teste) está documentado logo acima, em
   `LIVE TRADING`. Este é o maior gap restante do projeto como um
   todo — nenhuma fase consegue fechá-lo sem acesso de rede real.

**`Production Hardening`** (75% → 92%) — autenticação por token
(`X-API-Token`/`API_ACCESS_TOKEN`), rate limiting (`slowapi`), handler
global de exceção não tratada, shutdown gracioso via
`SIGTERM`/`SIGINT` com flush final de runtime state, e alerta externo
configurável via webhook (`core/services/alert_service.py`) — wireado
tanto no caminho de posição desprotegida quanto nos três pontos
`CRITICAL` novos da reconciliação de startup. `core/orchestrator/orchestrator.py`
(stub morto) removido.

**`Persistence Layer`** (84% → 90%) — `PRAGMA busy_timeout=5000` e
`scripts/backup_db.py` (backup timestamped com rotação, usando a API
de backup do `sqlite3` para uma cópia consistente mesmo em WAL).
PostgreSQL permanece fora de escopo, por decisão explícita, não por
lacuna.

**`Frontend`** (60% → 75%) — página `Tools.jsx` (optimizer/backtest
pela interface) documentada, antes ausente do README. Testes
automatizados (Vitest + Testing Library) cobrindo o wrapper de API
(`client.js`), `usePolling` e as páginas Dashboard/Settings — ainda
sem cobertura de `Tools.jsx` nem dos componentes visuais menores
(`TradesTable`, `PnlChart`, etc.), por isso não é 100%.

**`Deploy (Docker)`** (módulo novo, 90%) — `Dockerfile` multi-stage +
`docker-compose.yml`, testado manualmente de ponta a ponta (build das
três imagens, containers saudáveis, Runner conectando de verdade ao
WebSocket da Binance, `PUT /settings` persistindo via bind mount do
`.env`). Ver `DEPLOY (Docker)` abaixo e `docs/DEPLOYMENT.md`.

**Nota sobre estes percentuais:** os números acima são uma
autoavaliação qualitativa, não uma métrica calculada por uma
metodologia formal (cobertura de linhas, requisitos fechados, etc.)
— trate-os como uma indicação aproximada de maturidade relativa entre
módulos, não como um placar preciso. O maior gap restante do projeto
inteiro é a falta de validação contra a Binance real (testnet ou
mainnet) — item 3 de `Exchange Integration` acima — algo que só pode
ser fechado manualmente, fora deste ambiente de desenvolvimento.
