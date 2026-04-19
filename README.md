# Eatit

Eatit is a monorepo for a resume + JD driven AI mock interview product. This stage provides a local development scaffold for a Tauri desktop client, a FastAPI backend, and local infrastructure with PostgreSQL, Redis, and MinIO.

## Structure

- `apps/desktop`: Tauri 2.x + React 18 + TypeScript 5 + Vite desktop client
- `apps/api`: FastAPI backend with uv, Alembic, structlog, and test scaffold
- `packages/shared-types`: shared TypeScript types package

## Prerequisites

- Node.js 20+
- `pnpm` or `corepack pnpm`
- Python 3.11+
- `uv`
- Docker with Compose support
- Rust toolchain for Tauri desktop development

## Quick Start

1. Copy environment variables:

   ```bash
   cp .env.example .env
   cp apps/api/.env.example apps/api/.env
   ```

2. Install frontend workspace dependencies:

   ```bash
   pnpm install
   ```

   If `pnpm` is not available globally, use:

   ```bash
   corepack pnpm install
   ```

3. Install backend dependencies:

   ```bash
   cd apps/api && uv sync
   ```

4. Start local infrastructure:

   ```bash
   docker-compose up -d
   ```

5. Start the desktop app:

   ```bash
   cd apps/desktop && pnpm tauri dev
   ```

6. Start the API server:

   ```bash
   cd apps/api && uv run uvicorn app.main:app --reload
   ```

7. Verify the health endpoint:

   ```bash
   curl localhost:8000/health
   ```

8. Run backend tests:

   ```bash
   cd apps/api && uv run pytest
   ```

## Current Stage Scope

- Monorepo workspace wiring
- Desktop hello world shell with route debug entries
- API hello world shell with `/health`
- Docker Compose for PostgreSQL, Redis, and MinIO
- Shared types package placeholder

This README will be expanded as the project moves into real product modules.

## Phase 2 Snapshot

- Backend now includes the initial Postgres schema, Alembic migration, Pydantic API contracts, mock `/api/v1` endpoints, and a placeholder WebSocket session endpoint
- Desktop now includes typed API hooks in `apps/desktop/src/api` and shared contracts in `packages/shared-types`
- Current auth is a fixed mock dependency for local development and test wiring
