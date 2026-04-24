"""Standalone entrypoint for the bundled (PyInstaller) Eatit backend.

When Eatit.app launches on an end-user Mac, Tauri spawns this module
(frozen into a single `eatit-backend` binary) as a subprocess. We:

1. Pick a free port (or honor `EATIT_PORT` env if supplied, mostly for tests).
2. Ensure the local data directories exist under
   `~/Library/Application Support/Eatit/` when `APP_ENV=production`.
3. Run Alembic migrations programmatically so a fresh install creates
   the SQLite schema without needing a separate `alembic upgrade head`.
4. Print `EATIT_BACKEND_READY port=<port>` to stdout once uvicorn reports
   startup complete — the Rust side reads this line to learn which port
   to hand to the WebView.
5. Block the main thread running uvicorn until the OS kills the process
   (Tauri sends SIGTERM on quit).

This file is intentionally independent of any `uv run` shell wrapper so
PyInstaller can freeze it directly.
"""

from __future__ import annotations

import asyncio
import os
import socket
import sys
from pathlib import Path


def _pick_port() -> int:
    """Bind a random free TCP port, close, and return the number.

    There's a tiny race window where another process could grab the port
    between our close and uvicorn's bind, but on a desktop app with a
    single backend subprocess per user this is negligible.
    """
    env_port = os.environ.get("EATIT_PORT", "").strip()
    if env_port:
        return int(env_port)
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def _resource_root() -> Path:
    """Root directory containing bundled resources (alembic/, etc.).

    - Under PyInstaller: `sys._MEIPASS` — the extracted temp dir.
    - Otherwise (dev run via `python -m app.entrypoint`): the repo's
      `apps/api/` directory, derived from this file's path.
    """
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        return Path(meipass)
    return Path(__file__).resolve().parents[1]


def _ensure_data_dirs() -> None:
    """Make sure the configured SQLite + cache + storage directories exist."""
    # Import here so PyInstaller doesn't trigger the Settings parse during
    # its own bootstrap phase.
    from app.infra.config import get_settings, resolve_cache_dir, resolve_storage_dir

    settings = get_settings()
    for path in (
        resolve_cache_dir(settings.cache_dir, settings.app_env),
        resolve_storage_dir(settings.storage_dir, settings.app_env),
    ):
        path.mkdir(parents=True, exist_ok=True)

    # SQLite file parent directory — resolve the database URL the same
    # way the async engine does.
    from app.infra.config import resolve_database_url

    resolved = resolve_database_url(settings.database_url, settings.app_env)
    # sqlite+aiosqlite:///<abs path>
    if resolved.startswith("sqlite+aiosqlite:///"):
        db_path = Path(resolved.removeprefix("sqlite+aiosqlite:///"))
        db_path.parent.mkdir(parents=True, exist_ok=True)


def _run_migrations() -> None:
    """Run `alembic upgrade head` in-process against the configured DB.

    The migration scripts live at `<resource_root>/alembic/` — under dev
    that's `apps/api/alembic/`, under PyInstaller that's the unpacked
    `_MEIPASS/alembic/` from `--add-data`.
    """
    from alembic import command
    from alembic.config import Config

    from app.infra.config import get_settings, resolve_database_url

    settings = get_settings()
    alembic_dir = _resource_root() / "alembic"
    if not alembic_dir.exists():
        # Running the source tree from outside apps/api (e.g. editable install
        # from a weird cwd). Try the repo-relative fallback.
        alembic_dir = Path(__file__).resolve().parents[1] / "alembic"

    # Alembic's async env.py expects a sync driver URL for the offline
    # branch; for online (in-process) runs the config just needs
    # sqlalchemy.url. We reuse the resolved async URL — Alembic uses its
    # own sync engine built from this via env.py, which swaps aiosqlite
    # for sqlite when it needs to.
    # env.py sets `version_locations` at module top level, but Alembic's
    # `ScriptDirectory` is already built from the raw Config before env.py
    # gets a chance to run — so we have to spell it out here, mirroring the
    # alembic.ini entry the CLI flow reads.
    cfg = Config()
    cfg.set_main_option("script_location", str(alembic_dir))
    cfg.set_main_option(
        "version_locations", str(alembic_dir / "versions" / "mainline")
    )
    # Alembic defaults to splitting version_locations on whitespace, which
    # shreds paths like `/Volumes/Eatit 3/Eatit.app/Contents/Resources/...`
    # into `/Volumes/Eatit` + `3/Eatit.app/...` and makes ScriptDirectory
    # return zero heads, causing "Can't locate revision identified by X".
    # `os` uses os.pathsep (":" on macOS/Linux) so spaces in the path are
    # safe. Matches the alembic.ini setting for CLI parity.
    cfg.set_main_option("version_path_separator", "os")
    cfg.set_main_option(
        "sqlalchemy.url", resolve_database_url(settings.database_url, settings.app_env)
    )
    command.upgrade(cfg, "head")


def main() -> None:
    # Default to production if no APP_ENV was injected — the bundled
    # binary is always "production" from the user's machine's POV.
    os.environ.setdefault("APP_ENV", "production")

    port = _pick_port()
    os.environ["EATIT_PORT"] = str(port)

    _ensure_data_dirs()
    _run_migrations()

    # Deferred imports so migrations run before FastAPI's lifespan begins.
    import uvicorn

    from app.infra.logging import configure_logging, get_logger

    configure_logging()
    log = get_logger(__name__)
    log.info(
        "eatit.backend.bootstrap",
        port=port,
        resource_root=str(_resource_root()),
    )

    # Emit the contract line FIRST so Tauri can unblock the webview as
    # soon as we reach here, even though uvicorn itself takes a moment
    # to finish startup events.
    print(f"EATIT_BACKEND_READY port={port}", flush=True)

    uvicorn.run(
        "app.main:app",
        host="127.0.0.1",
        port=port,
        log_level="info",
        access_log=False,
    )


if __name__ == "__main__":
    # Multiprocessing under PyInstaller needs this guard to avoid a
    # re-entry loop on macOS (spawn start method).
    from multiprocessing import freeze_support

    freeze_support()
    main()
