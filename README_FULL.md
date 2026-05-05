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

## Bootstrap Automático
O projeto possui um sistema de bootstrap que:

- cria diretórios automaticamente
- garante __init__.py em todos módulos
- valida arquivos obrigatórios
- prepara ambiente Python
Arquivos:
scripts/start.bat
scripts/bootstrap.py

## Estrutura das pastas
crypto.bot/

├── apps/
│   ├── api/
│   │   └── main.py
│   │
│   ├── trader/
│   │   └── runner.py
│   │
│   └── ui/ (futuro)
│
├── core/
│   ├── workroom/
│   │   ├── bus.py
│   │   └── message.py
│   │
│   ├── agents/
│   │   ├── base_agent.py
│   │   ├── analyst_agent.py
│   │   ├── strategy_agent.py
│   │   ├── risk_agent.py
│   │   └── execution_agent.py
│   │
│   ├── orchestrator/
│   │   ├── trade_orchestrator.py
│   │   ├── state_machine.py
│   │   └── error_handler.py
│   │
│   ├── contracts/
│   │   ├── base.py
│   │   ├── messages.py
│   │   ├── strategy.py
│   │   ├── risk.py
│   │   └── execution.py
│   │
│   └── learning/ (futuro)
│
├── data/
│   ├── ingestion/
│   ├── features/
│   └── storage/
│
├── infra/
│   ├── config/
│   ├── logging/
│   └── database/
│
├── scripts/
│   ├── start.sh
│   ├── start.bat
│   └── validate.py
│
├── requirements.txt
├── README.md
├── README_FULL.md
└── PROJECT_PROMPT.txt

## DESCRIÇÃO DE CADA MÓDULO
📁 /apps

🔹apps/api/main.py
Responsável por:
subir o servidor FastAPI
expor endpoints (status, config, controle)
futuramente:
controle do bot
métricas
integração com UI

🔹 apps/trader/runner.py
Responsável por:
inicializar o sistema de trading
subir:
WorkRoom
Agents
Orchestrator
iniciar ciclo de mercado

📁 /core (CÉREBRO DO SISTEMA)
🔹 /core/workroom
bus.py
Event bus interno
responsável por:
distribuir mensagens entre agentes
simular “conversa”

message.py
estrutura base das mensagens
padrão:
{
  "type": "...",
  "sender": "...",
  "user_id": 0,
  "payload": {},
  "explanation": ""
}

🔹 /core/agents
base_agent.py
classe base de todos agentes
define:
on_message
publish

analyst_agent.py
analisa mercado
output:
tendência
volatilidade

strategy_agent.py
gera sinais de trade
output:
BUY / SELL
entry / stop / take

risk_agent.py
controla risco (CRÍTICO)
pode:
aprovar
reduzir posição
bloquear trade

execution_agent.py
executa ordens
modos:
paper (simulado)
live (real)

🔹 /core/orchestrator
trade_orchestrator.py
coordena o ciclo do trade
mantém contexto por trade

state_machine.py
controla estados do trade
impede transições inválidas

error_handler.py
captura falhas
define fallback seguro

🔹 /core/contracts
base.py
modelo base (Pydantic)
validação global

messages.py
tipos de mensagens:
MARKET_ANALYSIS
TRADE_PROPOSAL
etc

strategy.py
schema de estratégia

risk.py
schema de risco

execution.py
schema de execução

🔹 /core/learning (futuro)
treinamento automático
otimização de parâmetros
versionamento de modelos

📁 /data
ingestion
coleta dados (Binance WS)
features
indicadores técnicos
storage
persistência (SQLite/Postgres)

📁 /infra
config
configs globais
configs por usuário
logging
logs estruturados
database
acesso ao banco
isolamento por user_id (CRÍTICO)

📁 /scripts
start.sh
inicia sistema (Linux/mac)
start.bat
inicia sistema (Windows)
validate.py
valida estrutura do projeto

🔷 CONCEITOS FUNDAMENTAIS

🧠 Work Room
agentes se comunicam via mensagens
simula “time de traders”

🔄 State Machine
controla ciclo do trade
evita bugs e decisões inválidas

🎯 Orchestrator
garante ordem do fluxo
conecta agentes + estado

🔒 Multi-tenant
user_id obrigatório
isolamento total entre usuários

🧪 Modos
Paper → simulação
Live → dinheiro real

🤖 IA (futuro)
agente adicional
sugere melhorias
nunca executa sem aprovação

🔷 REGRAS DO SISTEMA (IMPORTANTÍSSIMO)
- Risk sempre pode bloquear trade
- Nenhum trade executa sem validação
- Nenhuma mensagem sem schema
- Nenhum dado sem user_id
- Nenhuma transição inválida de estado

🔷 FLUXO COMPLETO
Market Data
   ↓
Analyst Agent
   ↓
Strategy Agent
   ↓
Risk Agent
   ↓
Orchestrator
   ↓
Execution Agent
   ↓
Trade Result
   ↓
Learning (futuro)
