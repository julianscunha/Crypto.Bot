# Política de Segurança

## Reportando uma vulnerabilidade

**Não abra uma issue pública para vulnerabilidades de segurança.**

Use o [GitHub Security Advisories](https://github.com/julianscunha/Crypto.Bot/security/advisories/new)
deste repositório para reportar de forma privada. Inclua:

- Descrição da vulnerabilidade e impacto potencial.
- Passos para reproduzir (payload, endpoint, condição de execução).
- Se souber, o arquivo/linha afetado.

Você deve receber uma resposta inicial em até 5 dias úteis.

## O que é considerado vulnerabilidade aqui

Este é um bot de trading que pode movimentar dinheiro real. O que mais nos
interessa:

- Qualquer forma de contornar o gate `LIVE_TRADING_CONFIRMED` /
  `MODE`/`BINANCE_TESTNET` e disparar ordem real sem as três confirmações.
- Qualquer forma de burlar a validação de `user_id`/`symbol` em
  `RiskAgent`/`ExecutionAgent` (spoofing de tenant, execução em símbolo
  fora da allowlist).
- Vazamento de credenciais da Binance (`BINANCE_API_KEY`/`SECRET_KEY`) via
  log, erro, resposta de API ou qualquer outro canal.
- Bypass da autenticação por token (`X-API-Token`) nas rotas sensíveis
  (`PUT /settings`, `POST /runner/start|stop`).
- SQL injection, path traversal, ou qualquer forma de RCE.

## O que **não** é uma vulnerabilidade de segurança

- Bugs de lógica de trading (estratégia ruim, cálculo de risco discutível)
  — abra uma issue normal.
- Falta de validação contra a Binance real em ambiente de testnet/mainnet
  — já é uma limitação conhecida e documentada no [`README.md`](README.md#maturidade-do-projeto).
- Problemas de UI/UX — issue normal.

## Vulnerabilidades em dependências

Se a vulnerabilidade estiver numa dependência de terceiros (ex.: FastAPI,
SQLAlchemy, uma lib do `frontend/package.json`) e não no código deste
projeto, reporte diretamente ao mantenedor da dependência — mas nos avise
também via Security Advisories se ela for explorável através do
Crypto.Bot especificamente (ex.: input não sanitizado antes de chegar na
lib vulnerável).

## Versões suportadas

Este projeto não segue um ciclo de release com versões LTS. Só a branch
`main` recebe correções de segurança.

## Boas práticas ao rodar o próprio fork

- Nunca commite seu `.env` real — use `.env.example` como template.
- Se expor a API além de `localhost`, configure `API_ACCESS_TOKEN` — o
  próprio sistema avisa no boot se detectar isso ausente.
- Trate `LIVE_TRADING_CONFIRMED=true` como você trataria uma credencial de
  produção — é a única coisa entre o bot e ordens reais em dinheiro real.
