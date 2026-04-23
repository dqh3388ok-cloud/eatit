# Eatit

Eatit is a monorepo for a resume + JD driven AI mock interview product. The current local main track is a zero-container desktop-friendly stack built on Tauri, FastAPI, SQLite, diskcache, local filesystem storage, and an in-process asyncio task queue.

## Structure

- `apps/desktop`: Tauri 2.x + React 18 + TypeScript 5 + Vite desktop client
- `apps/api`: FastAPI backend with uv, Alembic, structlog, and test scaffold
- `packages/shared-types`: shared TypeScript types package

## Prerequisites

- Node.js 20+
- `pnpm` or `corepack pnpm`
- Python 3.11+
- `uv`
- Rust toolchain for Tauri desktop development

## Runtime Model

- Main local development path: no Docker required
- Default persistence: SQLite at `.data/eatit.db`
- Default cache: diskcache at `.data/cache`
- Default file storage: local filesystem at `.data/storage`
- Default background tasks: in-process asyncio task queue
- Optional only: `docker-compose.yml` for compatibility debugging of legacy PostgreSQL / Redis / MinIO behavior

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

4. Run SQLite migrations:

   ```bash
   cd apps/api && uv run alembic upgrade head
   ```

5. Start the API server:

   ```bash
   cd apps/api && uv run uvicorn app.main:app --reload
   ```

6. Verify the health endpoint:

   ```bash
   curl localhost:8000/health
   ```

7. Run backend tests:

   ```bash
   cd apps/api && uv run pytest -v
   ```

8. Start the desktop app:

   ```bash
   cd apps/desktop && corepack pnpm tauri dev
   ```

## 构建未签名 DMG

本地打一个未签名的 macOS 安装包用于自测或小范围分发:

```bash
rustup target add aarch64-apple-darwin   # 仅第一次需要
scripts/build-unsigned-dmg.sh
```

脚本封装了 `corepack pnpm build:dmg`(等价于 `tauri build --target aarch64-apple-darwin --bundles dmg`),完整 release 构建冷启动 10 分钟量级。产物路径:

```
apps/desktop/src-tauri/target/aarch64-apple-darwin/release/bundle/dmg/Eatit_0.1.0_aarch64.dmg
```

> ⚠️ 此 DMG 未经 Apple 代码签名与公证。**第一次打开需要在 访达 中右键 → 打开**,或到 系统设置 > 隐私与安全性 中手动放行。代码签名与 notarization 是后续迭代(Phase 5 P5.3)的事。

## Optional Compatibility Debugging

If you explicitly need to inspect legacy containerized behavior, you can start the optional stack:

   ```bash
   docker compose up -d
   ```

That stack is only for local debugging of PostgreSQL, Redis, and MinIO compatibility. It is not required for the main desktop application flow.

## Current Stage Scope

- Monorepo workspace wiring
- Desktop hello world shell with route debug entries
- API hello world shell with `/health`
- SQLite mainline persistence with local cache, storage, and task queue abstractions
- Optional Docker Compose stack for legacy infrastructure compatibility checks
- Shared types package placeholder

This README will be expanded as the project moves into real product modules.

## Phase 2 Snapshot

- Backend now includes the SQLite mainline schema, Alembic migration, Pydantic API contracts, mock `/api/v1` endpoints, and a placeholder WebSocket session endpoint
- Desktop now includes typed API hooks in `apps/desktop/src/api` and shared contracts in `packages/shared-types`
- Current auth is a fixed mock dependency for local development and test wiring
