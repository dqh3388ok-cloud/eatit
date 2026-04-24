# PyInstaller spec for the bundled Eatit backend.
#
# Output:  dist/eatit-backend/  (onedir layout — faster cold start and
#          easier to sign per-file than a onefile monolith)
# Entry:   app/entrypoint.py  (see its module docstring for protocol)
#
# Bundles:
#   - Alembic migrations (discovered via hidden path at runtime, see
#     app/entrypoint.py _resource_root)
#   - Jinja2 prompt templates under app/prompts/
#   - faster-whisper + CTranslate2 + PyAV native extensions
#   - onnxruntime runtime providers
#
# Run:  uv run pyinstaller eatit-backend.spec --noconfirm

# ruff: noqa
from __future__ import annotations

from pathlib import Path

from PyInstaller.utils.hooks import collect_all, collect_submodules

BLOCK_CIPHER = None
REPO = Path(".").resolve()   # invoked from apps/api/

# --- data files bundled alongside the binary ---------------------------------
datas = [
    # Alembic migration tree (env.py + versions/mainline/*.py + alembic.ini)
    (str(REPO / "alembic"), "alembic"),
    # Jinja2 agent prompts (render_prompt reads via FileSystemLoader)
    (str(REPO / "app" / "prompts"), "app/prompts"),
]

# --- native-extension packages pulled in as a whole --------------------------
binaries = []
hiddenimports: list[str] = [
    # Alembic's env.py loads our modules; be explicit because Alembic
    # uses importlib magic PyInstaller can miss.
    "app.main",
    "app.infra.db.session",
    "app.models",
    # Auto-reload mechanics from uvicorn — not needed in packaged mode but
    # import-time safe to include so we don't get surprise failures.
    "uvicorn.logging",
    "uvicorn.loops",
    "uvicorn.loops.auto",
    "uvicorn.protocols",
    "uvicorn.protocols.http",
    "uvicorn.protocols.http.auto",
    "uvicorn.protocols.websockets",
    "uvicorn.protocols.websockets.auto",
    "uvicorn.lifespan",
    "uvicorn.lifespan.on",
    # aiosqlite runs with uvloop's loop-aware interfaces
    "aiosqlite",
]

# Alembic versions are imported dynamically; make sure all mainline scripts
# end up in the bundle's Python module graph (in addition to datas above, which
# is what env.py actually reads from).
hiddenimports += collect_submodules("alembic")

# Libraries with complex metadata / native sidecars. `collect_all` returns
# (datas, binaries, hiddenimports) we append to each bucket.
for pkg in (
    "faster_whisper",
    "ctranslate2",
    "av",
    "onnxruntime",
    # LiteLLM ships model_prices_and_context_window_backup.json as a data
    # file next to the module; without collect_all PyInstaller drops it
    # and litellm crashes at import.
    "litellm",
    # Instructor similarly carries template JSON for mode configs.
    "instructor",
    # Tiktoken bundles BPE encoding data.
    "tiktoken",
    "tiktoken_ext",
):
    pkg_datas, pkg_binaries, pkg_hidden = collect_all(pkg)
    datas += pkg_datas
    binaries += pkg_binaries
    hiddenimports += pkg_hidden

# --- Analysis -----------------------------------------------------------------
a = Analysis(
    [str(REPO / "app" / "entrypoint.py")],
    pathex=[str(REPO)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=[
        # uv's own test harness; ctranslate2 lugs these in on some wheels
        "pytest",
        "tests",
    ],
    noarchive=False,
    optimize=0,
    cipher=BLOCK_CIPHER,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=BLOCK_CIPHER)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="eatit-backend",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="eatit-backend",
)
