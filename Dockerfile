# syntax=docker/dockerfile:1

# =====================================================
# STAGE: frontend-build
# =====================================================
#
# Builds the static frontend bundle. VITE_API_BASE_URL is baked in
# at build time (Vite inlines import.meta.env.* into the bundle --
# there's no way to change it at container-start time without
# rebuilding), so it must be passed as a build arg matching wherever
# the API will actually be reachable from the browser. See
# docker-compose.yml and docs/DEPLOYMENT.md.

FROM node:20-alpine AS frontend-build

WORKDIR /app/frontend

ARG VITE_API_BASE_URL=http://localhost:8000

ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}

COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

COPY frontend/ ./
RUN npm run build

# =====================================================
# STAGE: frontend (nginx serving the built bundle)
# =====================================================

FROM nginx:alpine AS frontend

COPY --from=frontend-build /app/frontend/dist /usr/share/nginx/html
COPY docker/nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

# =====================================================
# STAGE: backend (API and Runner share this image --
# docker-compose.yml selects the process via `command:`)
# =====================================================

FROM python:3.11-slim AS backend

WORKDIR /app

# gcc/build tools aren't needed -- every dependency in
# scripts/bootstrap/requirements.txt ships manylinux wheels.
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --no-cache-dir --upgrade pip

COPY scripts/bootstrap/requirements.txt ./scripts/bootstrap/requirements.txt
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --no-cache-dir -r scripts/bootstrap/requirements.txt

COPY apps/ ./apps/
COPY core/ ./core/
COPY data/ ./data/
COPY backtest/ ./backtest/
COPY scripts/ ./scripts/
COPY alembic/ ./alembic/
COPY alembic.ini ./alembic.ini
COPY __init__.py ./__init__.py

# data/storage/trades.db lives on a mounted volume in
# docker-compose.yml -- this just ensures the directory exists with
# sane permissions before the first container start creates it.
RUN mkdir -p /app/data/storage /app/logs

EXPOSE 8000

# Overridden by docker-compose.yml's `command:` for the runner
# service -- this default is the API.
CMD ["uvicorn", "apps.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
