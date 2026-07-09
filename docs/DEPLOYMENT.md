# Deploy com Docker

> Leia [`docs/README_FULL.md`](README_FULL.md) primeiro se ainda não
> conhece a arquitetura do projeto — este guia cobre só o empacotamento
> em containers, não repete o funcionamento do bot em si.

## Visão geral

```
┌─────────────┐      ┌─────────────┐      ┌─────────────┐
│  frontend   │ ───► │     api     │ ◄─── │   runner    │
│ (nginx:80,  │      │ (uvicorn,   │      │ (apps.trader│
│  porta 8080)│      │  porta 8000)│      │  .runner)   │
└─────────────┘      └──────┬──────┘      └──────┬──────┘
                             │                    │
                             └────────┬───────────┘
                                      ▼
                          volume `trades_db` (SQLite)
```

Três serviços, todos definidos em `docker-compose.yml`, construídos a
partir do mesmo `Dockerfile` multi-stage:

- **`frontend`** — está `target: frontend` do `Dockerfile` (build do
  bundle React/Vite num stage Node, servido por `nginx:alpine` num
  stage final). Porta `8080` publicada no host por padrão.
- **`api`** — `target: backend` do mesmo `Dockerfile`, rodando
  `uvicorn apps.api.main:app`. Porta `8000` publicada no host.
- **`runner`** — mesma imagem `backend`, comando
  `python -m apps.trader.runner`. Não expõe porta nenhuma (não é um
  servidor HTTP).

`api` e `runner` compartilham o volume nomeado `trades_db`
(`/app/data/storage`, onde vive `trades.db`) — é assim que o Runner
escreve trades e a API os lê, exatamente como já acontece hoje fora
do Docker quando os dois rodam como processos separados na mesma
máquina.

`api` e `runner` também montam o `.env` real do host como bind mount
(`./.env:/app/.env`) — não é só o `env_file:` do Compose (que injeta
variáveis uma única vez, na criação do container). `PUT /settings`
(o painel Settings do frontend) lê e escreve o arquivo `.env`
diretamente em disco via `core/config/settings_repository.py`; sem
esse bind mount, essas escritas cairiam na camada de filesystem
efêmera do container e seriam perdidas no próximo
`docker compose up`/recreate. Validado manualmente: `PUT /settings`
→ mudança aparece no `.env` do host → sobrevive a
`docker compose down && docker compose up`.

## Passo a passo

```bash
cp .env.example .env
# edite .env: pelo menos CORS_ALLOWED_ORIGINS=http://localhost:8080
# (a origem publicada pelo serviço frontend) e, se for expor além de
# localhost, API_ACCESS_TOKEN (ver "Segurança" abaixo)

docker compose up --build
```

- Frontend: `http://localhost:8080`
- API: `http://localhost:8000`

Testado manualmente de ponta a ponta neste repositório: as três
imagens buildam, os três containers sobem saudáveis, o Runner conecta
de verdade ao WebSocket da Binance (modo paper) e recebe klines, a
API responde em `/health`, o frontend serve o bundle em `8080`, CORS
libera a origem do frontend, e `PUT /settings` persiste no `.env` do
host e sobrevive a um `docker compose down && up`.

## Variáveis de ambiente relevantes para Docker

Além de tudo já documentado no `README.md`/`docs/README_FULL.md`
(`MODE`, `BINANCE_*`, etc.), duas variáveis existem especificamente
para setups multi-origem como este:

| Variável | Para quê |
|---|---|
| `CORS_ALLOWED_ORIGINS` | Lista separada por vírgula de origens que a API aceita via CORS. O padrão (`http://localhost:5173,http://127.0.0.1:5173`) é o dev server do Vite — **não** inclui a porta `8080` do frontend em Docker. Adicione `http://localhost:8080` (ou o host real, se publicado em outro lugar) antes de subir. |
| `VITE_API_BASE_URL` | Usada como *build arg* do stage `frontend-build` do `Dockerfile` (`docker-compose.yml` já repassa a variável de ambiente do host para o build). Precisa apontar para onde o **navegador** vai alcançar a API — não para o nome do serviço Docker (`api`), que só resolve dentro da rede interna do Compose. Rebuild da imagem do frontend é necessário sempre que isso mudar (é embutido no bundle JS em tempo de build pelo Vite, não lido em runtime). |

## Segurança antes de expor além de `localhost`

Por padrão (localhost apenas), `API_ACCESS_TOKEN` vazio é aceitável —
é exatamente o comportamento já documentado para uso local fora do
Docker. **Antes de publicar qualquer uma dessas portas além de
`localhost`** (um servidor remoto, um domínio público):

1. **Configure `API_ACCESS_TOKEN`** — sem isso, `PUT /settings`,
   `POST /runner/start` e `POST /runner/stop` ficam acessíveis para
   qualquer um que alcance a porta 8000. A própria API já loga um
   `WARNING` no startup se detectar essa combinação arriscada (ver
   Fase 2 do roadmap, `PRODUCTION HARDENING` em
   `docs/README_FULL.md`).
2. **Coloque um reverse proxy com TLS na frente** (nginx, Caddy,
   Traefik) — nem a API nem o nginx deste `docker-compose.yml`
   servem HTTPS diretamente. Tráfego sem TLS expõe o
   `X-API-Token` e as credenciais da Binance (quando configuradas via
   painel Settings) em texto puro.
3. **Restrinja `CORS_ALLOWED_ORIGINS`** ao(s) domínio(s) real(is) do
   frontend publicado — nunca use um wildcard aqui.

## Runner: gerenciado pelo Compose vs. pelo botão ▶ do frontend

Este é o único ponto onde o setup Docker diverge do comportamento
padrão fora de containers, e vale entender antes de usar em produção:

Fora do Docker, `POST /runner/start` (o botão ▶ do frontend) faz a
própria API iniciar `apps.trader.runner` como um **subprocesso do seu
próprio processo** (`core/services/process_manager_service.py`,
rastreado por PID file em `runtime/runner.pid`). Esse controle
depende de subprocess/PID compartilhado no mesmo host.

Com o `docker-compose.yml` como está, o serviço `runner` já roda
**sempre**, como container próprio, independente do frontend. Nesse
modo:

- **Não use o botão ▶/⏹ do frontend** — ele tentaria iniciar/parar um
  processo *dentro do container `api`*, que não é o mesmo processo (e
  nem o mesmo container) que o serviço `runner` do Compose. Os dois
  controles de lifecycle não se enxergam entre containers.
- Para parar/iniciar o bot, use `docker compose stop runner` /
  `docker compose start runner`.

Se preferir controlar o lifecycle pelo botão do frontend (como fora
do Docker), **comente o serviço `runner` inteiro** em
`docker-compose.yml` — nesse caso o container `api` passa a ser
responsável por criar o subprocesso do Runner sob demanda, como já
faz hoje fora do Docker.

## Backup do banco em Docker

`scripts/backup_db.py` (ver Fase 3 do roadmap,
`docs/README_FULL.md`) assume um caminho de arquivo local
(`data/storage/trades.db`) — para rodá-lo contra o volume Docker:

```bash
docker compose exec api python scripts/backup_db.py --keep 10
```

Os backups ficam dentro do volume `trades_db`
(`/app/data/storage/backups/`). Para copiá-los para o host:

```bash
docker cp $(docker compose ps -q api):/app/data/storage/backups ./backups
```
