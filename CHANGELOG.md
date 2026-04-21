# Changelog

## 0.1.0

- initialize stage-one monorepo scaffold
- add Tauri desktop hello world shell with five debug routes
- add FastAPI backend scaffold with health endpoint and test
- add Docker Compose for PostgreSQL, Redis, and MinIO

## 0.2.0

- add SQLAlchemy data model and initial Alembic migration for assets, sessions, turns, reports, and users
- add Parse / Framework / Compression / Report / NQ / NA / NUA schema layer under `apps/api/app/schemas`
- add mock REST endpoints under `/api/v1` with fixed mock auth dependency
- add WebSocket protocol skeleton with `client.*` / `server.*` event namespaces and binary/text frame dispatch
- add TypeScript shared contract mirror and desktop API/query/websocket client
- validate the initial migration against a real local PostgreSQL instance and fix duplicate enum creation by switching the migration to PostgreSQL-native enums with `create_type=False`

### Key Decisions

- Parse schema is split into `ParseResultPayload` for Agent output and `ParseResultResponse` for REST wrapper metadata
- WebSocket event names are fixed to `client.*` and `server.*`; binary frames are reserved for `client.audio.chunk`, text frames dispatch by `event`
- UUID primary keys use application-generated UUIDv7 via `uuid-utils`
- mock auth currently returns fixed user `01964b52-1a8d-7b10-8d75-f0d4c7f00001 / mock-user@eatit.local`
- auth placeholder lives in `apps/api/app/api/dependencies/auth.py`

## 0.2.5

- switch the local main track from PostgreSQL / Redis / MinIO / Celery to SQLite / diskcache / local filesystem storage / asyncio task queue
- move the original PostgreSQL Alembic migration into a legacy track and start a new SQLite mainline migration
- make ORM models dialect-agnostic by replacing database UUID columns with `String(36)`, `JSONB` with `JSON`, and database enums with string columns plus Python `StrEnum`
- enable SQLite desktop-friendly pragmas at engine startup: `journal_mode=WAL`, `synchronous=NORMAL`, and `foreign_keys=ON`
- add `CacheInterface` with a `DiskcacheBackend`
- add `StorageInterface` with a `LocalFilesystemBackend`
- add `TaskQueueInterface` with an `AsyncioBackend`
- update asset uploads to persist files through the storage abstraction instead of returning `mock://minio/...` placeholders
- update report generation to enqueue background work through the task queue abstraction instead of relying on Celery
- downgrade `docker-compose.yml` to an optional compatibility debugging tool instead of a required local runtime dependency
- update `README.md` to document the zero-container local development flow

### Key Decisions

- target users are C-end job seekers receiving a DMG installer, so the local main track must work without Docker, Colima, or any external services
- SQLite is the primary local database because it supports zero-configuration desktop distribution; the PostgreSQL migration is kept as a legacy reference for possible future cloud deployment
- cache, storage, and task execution now sit behind abstractions so the desktop build can stay lightweight while preserving a clean path back to Redis, object storage, or a distributed queue in the future
- development defaults use project-local `.data/` directories, while production defaults resolve to `~/Library/Application Support/Eatit/`
