# Contribuindo com o Crypto.Bot

Obrigado pelo interesse em contribuir. Este documento cobre como configurar
o ambiente, o que esperar do processo de revisão e as regras de domínio que
todo PR precisa respeitar.

## Antes de começar

- Leia o [`README.md`](README.md) para uma visão geral da arquitetura.
- Leia o `CLAUDE.md`/`AGENTS.md` na raiz do repo — cobrem as regras de
  domínio (EventBus, `user_id`, `entry_price`) e convenções de código que
  todo PR precisa seguir. Um PR que viole essas regras é rejeitado no review.
- Para bugs de segurança, **não abra uma issue pública** — veja
  [`SECURITY.md`](SECURITY.md).

## Configurando o ambiente

```bash
git clone https://github.com/julianscunha/Crypto.Bot.git
cd Crypto.Bot
cp .env.example .env

pip install -r scripts/bootstrap/requirements.txt pytest pytest-asyncio pytest-cov ruff

cd frontend && npm install && cd ..
```

## Antes de abrir um PR

Rode a mesma suíte que o CI roda:

```bash
ruff check .
python -m pytest tests/ -q

cd frontend
npm run lint
npm test
```

Um PR só é aceito com CI verde (`.github/workflows/ci.yml`).

## Escrevendo o PR

- **Escopo pequeno e focado.** Um PR resolve uma coisa. Mudanças grandes
  (nova feature, refactor amplo) devem ser discutidas numa issue antes.
- **Teste o que você mudou.** Lógica em `core/agents/` ou `core/services/`
  sem teste correspondente não é aceita — veja os arquivos em `tests/` como
  referência de padrão (mock via `monkeypatch`, sem mock de banco real).
- **Nunca remova ou contorne**:
  - o gate `LIVE_TRADING_CONFIRMED` e as checagens de `MODE`/`BINANCE_TESTNET`;
  - a validação de `user_id`/`symbol` em `RiskAgent`/`ExecutionAgent`;
  - a comunicação via `EventBus` entre agentes (nunca chamada direta).
- **Nunca commite** credenciais, `.env` real, ou arquivos de
  `data/storage/`/`logs/` — já cobertos pelo `.gitignore`, mas confira o
  `git status` antes de dar push.
- Mensagens de commit em português ou inglês, descrevendo o **porquê**, não
  só o que mudou.

## Estilo de código

- Python: `ruff check .` precisa passar limpo. Sem type hints obrigatórios,
  mas prefira nomes claros a comentários explicando o óbvio.
- Frontend: `oxlint` + os tokens de design em `frontend/src/index.css`
  (`--bg-*`, `--text-*`, `--signal-*`) — evite cor/valor hardcoded fora dos
  tokens existentes.
- Sem abstração especulativa: se só existe um caso de uso, não crie
  interface/config genérica para um hipotético segundo caso.

## Dúvidas

Abra uma issue com a tag `question` ou comece a discussão direto no PR.
