# Phase 2.5 Migration Plan

## Decision Context

This document replaces the earlier infra-oriented simplification assessment with a product-driven migration decision. The target users are C-end job seekers, including AI product managers, technical PMs, senior engineers, and project leads. They are expected to install a DMG and use the app directly; they are not expected to install Docker, Colima, PostgreSQL, Redis, MinIO, or any terminal tooling. Because "double-click and use" is a hard product requirement, the app must not depend on containerized infrastructure in its primary runtime path.

## Final Decision

Phase 2.5 will move the local app runtime to a zero-config architecture:

- `PostgreSQL` → `SQLite`
- `Redis` → `diskcache`
- `MinIO` → local filesystem storage
- `Celery` → an abstracted `asyncio` task backend

This is not a temporary dev-only shortcut. It is the mainline architecture for the local desktop product.

## Why SQLite Is the Chosen Primary Path

- The product is distributed as a DMG for non-technical end users.
- Requiring Colima or any local container runtime is incompatible with that audience.
- Requiring users to manually start PostgreSQL is also incompatible with zero-configuration onboarding.
- SQLite ships as an embedded database and fits the current single-user desktop execution model.
- The app still keeps future cloud compatibility by making the model layer dialect-agnostic instead of SQLite-specific.

## Mainline Architecture Changes

### 1. Database: PostgreSQL → SQLite

#### Scope

- `apps/api/app/infra/db/` will move from `asyncpg` to `aiosqlite`.
- The database URL will point to a file-backed SQLite database by default.
- SQLite will run in WAL mode and enforce key pragmas at engine initialization.

#### Target database locations

- Development: `.data/eatit.db`
- Production desktop app: `~/Library/Application Support/Eatit/eatit.db`
- Override path: `DATABASE_URL`

#### Dialect-agnostic model replacements

- `UUID` columns:
  - Replace PostgreSQL `UUID` columns with `String(36)`.
  - Keep application-side UUIDv7 generation unchanged.
- `JSONB` columns:
  - Replace PostgreSQL `JSONB` with SQLAlchemy `JSON`.
  - SQLite will persist JSON as text-backed JSON data.
  - Future PostgreSQL recovery stays possible because the ORM type remains abstract.
- Database-native enums:
  - Replace SQLAlchemy `Enum(...)` columns with `String`.
  - Keep Python enums in the domain/schema layer for validation and serialization.
- Driver:
  - Replace `asyncpg` with `aiosqlite`.

#### SQLite engine requirements

- Enable `PRAGMA journal_mode=WAL`
- Enable `PRAGMA synchronous=NORMAL`
- Enable `PRAGMA foreign_keys=ON`

#### Migration strategy

- Do not attempt a dual-compatible migration chain.
- Keep the existing PostgreSQL migration in `apps/api/alembic/versions/` as a legacy reference for possible future cloud/server deployments.
- Rename it to make that status explicit, for example with a `_postgres_legacy` suffix.
- Start a new SQLite mainline migration:
  - `20260421_0000_initial_sqlite.py`

#### Files expected to change

- `apps/api/app/infra/config.py`
- `apps/api/app/infra/db/session.py`
- `apps/api/app/models/base.py`
- `apps/api/app/models/asset.py`
- `apps/api/app/models/session.py`
- `apps/api/app/models/report.py`
- `apps/api/alembic/env.py`
- `apps/api/alembic/versions/20260419_1600_initial_data_model.py`
- `apps/api/alembic/versions/20260421_0000_initial_sqlite.py`
- `apps/api/pyproject.toml`
- `apps/api/tests/*`
- `README.md`
- `CHANGELOG.md`

#### Risk assessment

- This is still the highest-risk migration in phase 2.5 because it touches every persisted entity.
- Existing PostgreSQL-specific migration logic cannot be reused as the mainline.
- SQLite concurrency is weaker than PostgreSQL, so WAL mode and disciplined write patterns are required.
- Test coverage must be rerun in full after the migration because the storage substrate changes materially.

#### Recommended implementation strategy

- First make the ORM layer dialect-agnostic.
- Then add the new SQLite initial migration.
- Then repoint tests to SQLite and rerun the full phase 2 suite.
- Keep PostgreSQL legacy migration files only as historical and future cloud references, not as active local runtime dependencies.

### 2. Cache: Redis → diskcache

#### Scope

- Introduce `app/infra/cache/`.
- Add a `CacheInterface`.
- Provide a `DiskcacheBackend`.
- Business code must depend on the interface, not `diskcache` directly.

#### Why this change is aligned with the product

- A local desktop app does not benefit from making end users run Redis.
- `diskcache` is sufficient for local memoization, polling state, and small single-machine cache workloads.
- Phase 2 does not yet rely on Redis semantics, so now is the cleanest time to introduce the abstraction.

#### Files expected to change

- `apps/api/app/infra/cache/`
- `apps/api/app/infra/config.py`
- `apps/api/pyproject.toml`
- future domain modules that need caching
- `README.md`
- `CHANGELOG.md`

#### Risk assessment

- Low risk if the abstraction boundary is introduced before any Redis-like usage spreads.
- `diskcache` must not be treated as a drop-in Redis replacement for queues, pub/sub, or distributed locks.

#### Recommended implementation strategy

- Introduce the interface first.
- Use `diskcache` only for explicitly local cache scenarios.
- Do not expose `diskcache` objects outside the backend implementation.

### 3. Storage: MinIO → local filesystem

#### Scope

- Introduce `app/infra/storage/`.
- Add a `StorageInterface`.
- Provide a `LocalFilesystemBackend`.
- Keep database file refs opaque instead of storing raw physical paths as business identifiers.

#### Target storage locations

- Development: `.data/storage/`
- Production desktop app: `~/Library/Application Support/Eatit/storage/`

#### Why this change is aligned with the product

- End users should not need a local object store.
- The app already behaves locally and stores only file refs today.
- Local filesystem storage is the most natural zero-config storage backend for a desktop application.

#### Files expected to change

- `apps/api/app/infra/storage/`
- `apps/api/app/infra/config.py`
- `apps/api/app/domain/assets/service.py`
- `apps/api/pyproject.toml`
- `README.md`
- `CHANGELOG.md`

#### Risk assessment

- Low risk if the storage ref remains opaque.
- Main operational risks are filename sanitization, directory creation, and migration of later object-storage-compatible assumptions.

#### Recommended implementation strategy

- Make local filesystem the default backend.
- Preserve a storage abstraction so a future cloud or OSS backend can be added without changing route contracts or database shape.

### 4. Task Queue: Celery → asyncio

#### Scope

- Introduce `app/infra/tasks/`.
- Add a `TaskQueueInterface`.
- Provide an `AsyncioBackend`.
- Prevent raw `asyncio.create_task(...)` calls from leaking into route and domain code.

#### Why this change is aligned with the product

- A local desktop app should not require a separate worker process or Redis broker just to generate a report.
- The report generation path can remain asynchronous from the user's point of view while still running in-process.

#### Files expected to change

- `apps/api/app/infra/tasks/`
- future `apps/api/app/tasks/`
- `apps/api/app/domain/reports/service.py`
- `apps/api/app/api/routes/sessions.py`
- `apps/api/pyproject.toml`
- `README.md`
- `CHANGELOG.md`

#### Risk assessment

- Moderate risk if long-running work becomes heavy enough to block the single app process.
- In-process tasks are less durable than queue-backed workers across crashes and restarts.
- This is acceptable for the current local-first desktop target if task state is still reflected in the database.

#### Recommended implementation strategy

- Build the abstraction first.
- Use an `AsyncioBackend` as the local mainline implementation.
- Persist task/report state in the database so the UI can still poll durable status.

## docker-compose Policy After Migration

`docker-compose.yml` stays in the repo, but only as an optional developer compatibility tool.

The file should be clearly annotated to say:

- It is only for development-time Redis/MinIO compatibility experiments.
- The production desktop app does not require containers.
- End users do not need Docker, Colima, or Docker Compose.

The README should be updated the same way:

- Local app startup must not mention Colima as a prerequisite.
- Container tooling should be documented only as an optional compatibility/debug path.

## Why the PostgreSQL Migration Is Still Kept

The original PostgreSQL migration should remain in the repository as legacy infrastructure knowledge because:

- it documents the original relational design in a production-grade server database,
- it may be useful if a future cloud or team edition revives PostgreSQL,
- it preserves the architectural history of phase 2.

However, it is no longer the active migration mainline for the local desktop product.

## Phase 2.5 Execution Order

1. Update the migration plan and docs to reflect the desktop zero-config decision.
2. Migrate the ORM and DB infrastructure to SQLite.
3. Add the new SQLite initial migration and retire the PostgreSQL migration to legacy status.
4. Introduce `CacheInterface` and `DiskcacheBackend`.
5. Introduce `StorageInterface` and `LocalFilesystemBackend`.
6. Introduce `TaskQueueInterface` and `AsyncioBackend`.
7. Re-run all tests and ensure the phase 2 happy path still passes on SQLite.
8. Update `README.md` and `CHANGELOG.md`.

## Overall Recommendation

- Make SQLite the primary local database now.
- Make local filesystem storage the primary storage backend now.
- Introduce cache and task queue abstractions now so phase 3 can build on stable local-only interfaces.
- Keep legacy PostgreSQL migration files only as historical and future cloud references.
