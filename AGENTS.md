# Repository Guidelines

## Project Structure & Module Organization
- `apps/` contains the runnable entry points for the API and trader process.
- `core/` holds the trading engine, agents, services, configuration, and event bus.
- `data/` contains persistence models, repositories, ingestion, and feature helpers.
- `backtest/` contains replay, optimizer, and reporting code plus fixture datasets in `backtest/datasets/`.
- `frontend/` is the React + Vite dashboard.
- `tests/` contains the pytest suite; migrations live in `alembic/versions/`.

## Build, Test, and Development Commands
- `./scripts/start.ps1` or `./scripts/start.sh` starts the interactive launcher for API, runner, backtest, and frontend.
- `python -m pytest tests/` runs the backend test suite with the isolated test database setup from `tests/conftest.py`.
- `alembic upgrade head` applies database migrations.
- In `frontend/`, use `npm install`, `npm run dev`, `npm run build`, and `npm run lint` for local UI work.

## Coding Style & Naming Conventions
- Python code follows async-first event-driven patterns. Keep agents on `async def on_message`, and route communication through the EventBus.
- Use `snake_case` for functions, modules, and variables; `PascalCase` for classes and agent names.
- Preserve the repository rules: do not remove `user_id`, do not break payload contracts, do not use `payload.price`, and prefer `entry_price`.
- Frontend components use `PascalCase` filenames and exports, hooks use `use*`, and JS style matches the existing Vite codebase.

## Testing Guidelines
- Pytest is configured via `pytest.ini` with `tests/` as the default test root and `test_*.py` naming.
- Prefer focused tests next to the behavior being changed. Add coverage for message flow, repositories, services, and migration effects when relevant.
- Run the full suite before opening a PR; use frontend lint/build checks when UI code changes.

## Commit & Pull Request Guidelines
- Commit history uses short imperative summaries, often with prefixes like `feat:` or `chore:`. Keep messages focused and descriptive.
- PRs should explain the change, note any risk or operational impact, and link related issues when available.
- Include screenshots or short recordings for frontend changes, and mention any migration or startup steps reviewers need to run.

## Security & Configuration Tips
- Do not commit live API keys, secrets, or local runtime artifacts such as logs or SQLite data.
- Confirm configuration changes against `README.md`, `scripts/bootstrap/requirements.txt`, and the relevant `core/config/` module before merging.
