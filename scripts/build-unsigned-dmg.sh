#!/usr/bin/env bash
# Build an unsigned .dmg of the Eatit desktop app for local/ad-hoc testing.
#
# Prereqs on the host machine:
#   - Xcode Command Line Tools (`xcode-select --install`)
#   - Rust toolchain with the aarch64-apple-darwin target:
#       rustup target add aarch64-apple-darwin
#   - Node 20+ and `corepack enable`
#
# The resulting .dmg is NOT code-signed. First-time launch on another Mac
# requires right-click → Open to bypass Gatekeeper. Signing + notarization
# are handled separately in Phase 5's P5.3 track (deferred).
#
# Usage:
#   scripts/build-unsigned-dmg.sh
#
# Build time: ~10 minutes cold, a few minutes incremental.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
DESKTOP_DIR="${REPO_ROOT}/apps/desktop"
BUNDLE_DIR="${DESKTOP_DIR}/src-tauri/target/aarch64-apple-darwin/release/bundle/dmg"

if [[ ! -d "${DESKTOP_DIR}" ]]; then
  echo "error: expected ${DESKTOP_DIR} to exist — are you running this from the repo?" >&2
  exit 1
fi

if ! command -v corepack >/dev/null 2>&1; then
  echo "error: corepack not found on PATH. Install Node 20+ and run 'corepack enable'." >&2
  exit 1
fi

echo ">> building Eatit unsigned DMG (target: aarch64-apple-darwin) ..."
cd "${DESKTOP_DIR}"
corepack pnpm build:dmg

echo ""
echo ">> built. looking for .dmg in ${BUNDLE_DIR}"
if [[ -d "${BUNDLE_DIR}" ]]; then
  find "${BUNDLE_DIR}" -maxdepth 1 -name "*.dmg" -print
else
  echo "warning: bundle directory not found; check build logs above." >&2
fi

echo ""
echo "注意:此 DMG 未签名,首次打开需要在 访达 中右键 → 打开,"
echo "      或到 系统设置 > 隐私与安全性 中放行。"
