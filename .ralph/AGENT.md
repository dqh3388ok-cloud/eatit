# Eatit Agent Build / Test / Run Instructions

## Project layout

```
eatit/
├── apps/
│   ├── api/          # FastAPI backend (Python 3.11 + uv)
│   └── desktop/      # Tauri 2.10.3 + React 18 + Vite
├── packages/
│   └── shared-types/ # TS types shared between frontend packages
├── .data/            # SQLite DB + cache + storage (gitignored)
├── .env / apps/api/.env   # user's local env (gitignored)
└── .ralph/           # this directory (DO NOT modify)
```

## Context refresh (run before first iteration on a section)

```bash
# Where you are
pwd && git branch --show-current && git log --oneline -5

# Backend tree + migrations
ls apps/api/app/
cd apps/api && uv run alembic current && cd ../..

# Frontend pages currently
ls apps/desktop/src/pages/ apps/desktop/src/components/
```

## Backend (apps/api/)

Activate:
```bash
cd apps/api
unset VIRTUAL_ENV    # avoid a stale VIRTUAL_ENV leak from parent shell
```

Add / update Python deps:
```bash
uv add <package>         # runtime
uv add --dev <package>   # dev-only
```

Run:
```bash
uv run uvicorn app.main:app --reload   # :8000
uv run pytest -v                        # all tests
uv run pytest tests/infra/test_llm.py   # one file
uv run alembic upgrade head
uv run alembic revision -m "<message>" --autogenerate
```

Migrations live in `apps/api/alembic/versions/mainline/`. New revisions
should follow the naming pattern `YYYYMMDD_NNNN_<snake>.py` and chain
`down_revision` to the latest head.

## Frontend (apps/desktop/)

```bash
cd apps/desktop

# deps
corepack pnpm install
corepack pnpm add <pkg>          # runtime
corepack pnpm add -D <pkg>       # dev

# verify
corepack pnpm exec tsc --noEmit
corepack pnpm lint
corepack pnpm build

# run (Vite only, no Tauri shell)
corepack pnpm dev                # :1420

# run (full Tauri dev window; slow first build)
corepack pnpm tauri dev
```

## Rust / Tauri (apps/desktop/src-tauri/)

```bash
source "$HOME/.cargo/env"
cd apps/desktop/src-tauri
cargo check
cargo test
cargo add <crate>
```

Registered Tauri commands must be added to the
`invoke_handler(tauri::generate_handler![...])` list in
`apps/desktop/src-tauri/src/lib.rs`.

## Shared conventions

- **No `/Users/shixuan/...` absolute paths** in source, tests, or docs.
  Use relative paths or `~/`.
- **Commits**: Conventional Commits. One section = one commit. Do NOT
  push to remote (Ralph stays local).
- **Line width**: Python 100 (ruff), TS follows existing Prettier config.
- **Python async**: all DB / IO paths use `async def` — pytest-asyncio
  is in `auto` mode so just `async def test_*` works.
- **Paths in tests**: use `tmp_path` fixture for filesystem, in-memory
  `sqlite+aiosqlite:///:memory:` for DB.

## Key state to remember

- Mock user is defined in `apps/api/app/api/dependencies/auth.py`
  (MOCK_USER_ID / MOCK_USER_EMAIL). There is no real auth in Phase 3.
- LLM key NEVER goes in env files or logs. It travels as a base64
  JSON payload in the `X-LLM-Config` HTTP header, parsed by
  `app/api/middleware/llm_config.py` onto `request.state.llm_config`.
  The desktop keychain at service=`com.eatit.desktop`
  account=`llm-config` holds it.
- Phase 2 mock routes under `apps/api/app/api/routes/` still exist.
  P3.5 replaces their bodies with real agent calls — don't delete the
  route files themselves, rewrite their bodies.
