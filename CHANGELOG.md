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

### Key Decisions

- Parse schema is split into `ParseResultPayload` for Agent output and `ParseResultResponse` for REST wrapper metadata
- WebSocket event names are fixed to `client.*` and `server.*`; binary frames are reserved for `client.audio.chunk`, text frames dispatch by `event`
- UUID primary keys use application-generated UUIDv7 via `uuid-utils`
- mock auth currently returns fixed user `01964b52-1a8d-7b10-8d75-f0d4c7f00001 / mock-user@eatit.local`
- auth placeholder lives in `apps/api/app/api/dependencies/auth.py`
