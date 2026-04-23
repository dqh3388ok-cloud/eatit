# Phase 5 Sections — 生产就绪 (minus code signing)

Phase 5 gets Eatit to "user can double-click and use it" — minus the
Apple Developer Program cert that blocks notarization. Sections 5.1,
5.2, 5.4, 5.5, 5.6 ship tonight. 5.3 (signing + notarization) is
**explicitly skipped** until the user completes Apple Dev enrollment;
a separate section P5.3 is pre-scoped in the spec so Ralph can pick it
up later with zero ambiguity.

All Phase 3 / 3.5 / 4 hard constraints carry over (no key leaks, WS
first-frame, TaskGroup cleanup, Sentry context must NOT include LLM
config / Azure key / user answer text).

## Execution order

| # | Section | Deps | Commit prefix |
|---|---|---|---|
| 1 | **P5.1 Real app icon** | — | `chore(desktop): real brand icons` (if user gives image; else skip) |
| 2 | **P5.2 Unsigned DMG build** | 5.1 (optional) | `build(desktop): tauri build config + unsigned dmg script` |
| 3 | **P5.4 PDF export report** | — | `feat(desktop): print-to-PDF on report page` |
| 4 | **P5.5 Sentry scaffold** | — | `feat(observability): sentry scaffold with secret redaction` |
| 5 | **P5.6 Error boundaries + reconnect** | — | `feat(ux): unified error boundary + ws reconnect` |
| 6 | **P5.X Test sweep + build smoke** | 1–5 | `test: phase 5 smoke + tauri build dry run` |

**Skipped (blocked by user action):**
- P5.3 Code signing + notarization — needs Apple Developer Program + Dev ID Application cert + Team ID + app-specific password

---

## P5.1 — Real app icon

**Goal.** Replace the placeholder solid-blue 1024×1024 PNG generated
in Phase 3 with a real brand image.

**Precondition.** User provides a PNG ≥ 1024×1024 at a known path (we
default to `assets/brand/icon.png` in the repo root — if missing, this
section is a no-op and Ralph moves on).

**Steps (if source image exists):**
1. `source $HOME/.cargo/env && cd apps/desktop && corepack pnpm tauri icon ../../assets/brand/icon.png`
2. Verify `apps/desktop/src-tauri/icons/icon.{png,icns,ico}` all regenerated with non-trivial file sizes (> 4KB each, because the blue placeholder is ~2KB)

**If source missing:** `echo "no real icon provided; skipping"` and exit the section cleanly without committing.

**Commit (conditional).** `chore(desktop): real brand icons`

---

## P5.2 — Unsigned DMG build

**Goal.** Produce a runnable `.app` and `.dmg` from the current repo,
unsigned. User can right-click-open the `.dmg` → drag the `.app` to
Applications → right-click → "Open" to bypass Gatekeeper.

**Files:**
- `apps/desktop/src-tauri/tauri.conf.json`:
  - Ensure `bundle.active = true` (already is)
  - `bundle.targets = "dmg"` (or `["dmg", "app"]`)
  - `bundle.macOS.minimumSystemVersion = "12.0"` (Monterey+)
  - `bundle.macOS.providerShortName = null` (leave unset; signing config lives in P5.3)
  - `bundle.identifier = "com.eatit.desktop"` (already is)
  - `bundle.category = "Productivity"` — for App Store metadata later
- `apps/desktop/package.json` — add script `"build:dmg": "tauri build --target aarch64-apple-darwin --bundles dmg"`
- `scripts/build-unsigned-dmg.sh` (new executable) — wraps the pnpm call, prints the resulting .dmg path, reminds the user "此 DMG 未签名,首次打开需要右键 → 打开"
- `README.md` — add a "构建未签名 DMG" section with the one-command instruction + signing caveat
- `.gitignore` — ensure `apps/desktop/src-tauri/target/release/bundle/` is ignored (Tauri's default respects this but confirm)

**Verification (in commit body):**
- `scripts/build-unsigned-dmg.sh` produces a .dmg (don't block the commit on the build completing — it takes 10+ minutes; Ralph reports the command works without running it to completion, unless CB allows)

**Commit.** `build(desktop): tauri build config + unsigned dmg script`

---

## P5.4 — PDF export report

**Goal.** Add a "导出 PDF" button to the ReportPage that produces a
clean PDF of the current report via the browser's print-to-PDF flow.

**Files (apps/desktop/src/):**
- `pages/ReportPage.tsx` — add button at the top right: "导出 PDF";
  onClick → `window.print()`
- `pages/report/print.css` (new, scoped import in ReportPage):
  - Hide sidebar / topbar / action buttons in `@media print`
  - Force light background, black text, single-column layout
  - Ensure `PassProbabilityRing` SVG prints correctly (no `stroke-dasharray` animation frozen at 0)
  - Page-break hints on `ReasonRow` boundaries so long reports paginate clean
- `components/AppShell.tsx` — `@media print { .sidebar, .topbar { display: none } }` block added (or moved to `index.css` under a `@media print` section)

**Acceptance:**
- `pnpm exec tsc --noEmit` + `pnpm lint` clean
- `grep -n "window.print\|@media print" apps/desktop/src/` — both hit

**Manual note in commit body:** "User verifies via Cmd+P preview on
the report page; Tauri WebView supports save-as-PDF natively via the
print dialog."

**Commit.** `feat(desktop): print-to-PDF on report page`

---

## P5.5 — Sentry scaffold

**Goal.** Wire Sentry into both backend and desktop app with DSN from
env. If DSN is empty (default), Sentry stays disabled — no runtime
overhead, no traffic, but the code paths exist so flipping the DSN in
`.env` activates it end-to-end.

**Hard invariant (extends A1).** Sentry breadcrumbs / context / events
MUST NEVER contain:
- `X-LLM-Config` header value or any decoded LLMConfig field
- `AZURE_SPEECH_KEY` or `AZURE_SPEECH_REGION` env value
- Raw audio bytes
- `InterviewTurn.answer` content (it's the candidate's words; PII risk)

**Files (apps/api/):**
- `app/infra/observability/sentry.py` (new):
  - `init_sentry(dsn, environment)` — no-op if dsn empty
  - `before_send(event, hint)` hook that REDACTS the forbidden keys (recursively walk event dict, replace matches with `"<redacted>"`)
  - Tests: 4 cases
    1. init with empty DSN → client is None, no network activity
    2. `before_send` redacts an event containing `X-LLM-Config` header
    3. `before_send` redacts an event containing `AZURE_SPEECH_KEY`
    4. `before_send` redacts an event whose `extra.answer` field matches `InterviewTurn.answer` pattern (any free-text field named `answer`)
- `app/main.py` — call `init_sentry(settings.sentry_dsn, settings.app_env)` in lifespan startup
- `app/infra/config.py` — `sentry_dsn: str = ""` already exists; no change

**Files (apps/desktop/src/):**
- `lib/sentry.ts` (new):
  - `initSentry(dsn, environment)` using `@sentry/react`
  - Integration: `BrowserTracing`, but set `tracesSampleRate: 0.1`
  - `beforeSend` hook mirroring backend — redact any header / env that matches the forbidden list
- `main.tsx` — call before `ReactDOM.createRoot`
- `api/client.ts` — ensure axios response interceptor does NOT log the request body to Sentry (it may contain `X-LLM-Config` in headers)

**Deps:**
- Backend: `sentry-sdk` already in pyproject
- Frontend: `corepack pnpm add -D @sentry/react` (or runtime dep — pick the smaller install; likely runtime)

**Acceptance:**
- `apps/api/`: `uv run pytest tests/infra/test_sentry.py` 4 cases green
- `apps/desktop/`: `pnpm exec tsc --noEmit` + `pnpm lint` clean
- `rg -n "X-LLM-Config|AZURE_SPEECH_KEY" apps/api/app/infra/observability/ apps/desktop/src/lib/sentry.ts` — matches only the redaction rules (never a value)

**Commit.** `feat(observability): sentry scaffold with secret redaction`

---

## P5.6 — Error boundaries + WS reconnect + friendly errors

**Goal.** Every error path in the desktop UI should render a
purposeful message, not "Network Error" or a blank screen.

**Sub-tasks:**

### 5.6a Backend unified exception handler
- `app/main.py` — add `@app.exception_handler(Exception)` that catches uncaught exceptions, logs at ERROR, and returns 500 with `{detail: "内部错误,请稍后重试", request_id}` — CORS headers preserved via FastAPI's proper handler flow
- LLMError / ASRError / DB error subclasses get their own handlers mapping to user-friendly 502 / 503 detail strings

### 5.6b WS auto-reconnect on the desktop side
- `pages/InterviewPage.tsx` — on `onclose` (code ≠ 1000 normal closure), display a "connection lost, reconnecting..." banner and reopen after 1s backoff, up to 3 attempts
- Preserve the current XState machine state across reconnect (don't restart the interview)
- New top-level connectivity indicator in AppShell topbar: green dot / red dot with tooltip

### 5.6c Friendly error toasts
- `components/Toast.tsx` (new, minimal) — small toast at bottom-right via a global store
- Axios interceptor dispatches a toast when a request fails in a way the caller doesn't already handle (network 5xx, 502 LLM error, etc.)
- LLM context overflow / auth / rate-limit errors get specific toast copy (already mapped in backend; just render `detail` field)

### 5.6d Offline banner
- `components/OfflineBanner.tsx` — listens to `navigator.onLine` + a heartbeat ping to `/health` every 20s; shows banner when offline

**Acceptance:**
- `pnpm exec tsc --noEmit` + `pnpm lint` clean
- Add 3 backend tests for the new exception handler (unknown exc, LLMError subclass, DB IntegrityError)

**Commit.** `feat(ux): unified error boundary + ws reconnect`

---

## P5.X — Test sweep + build smoke

- Run full backend pytest + frontend tsc/lint/build + cargo check
- Run `corepack pnpm tauri build --target aarch64-apple-darwin --bundles dmg` smoke — if it fails for any reason other than signing (we're building unsigned), stop and surface the error; if signing-related (certificate not found), note it and proceed; if build completes, report the .dmg size
- `git status` clean, all `[x]`

**Commit.** `test: phase 5 smoke + tauri build dry run`

---

## P5.3 — Code signing + notarization (SKIPPED TONIGHT)

Spec'd here so the user can trigger Ralph on it later with zero
thinking. Blocked until user provides:
1. `APPLE_SIGNING_IDENTITY` — "Developer ID Application: <Name> (<Team ID>)"
2. `APPLE_ID` — email used for Apple Developer account
3. `APPLE_PASSWORD` — app-specific password (not Apple ID password)
4. `APPLE_TEAM_ID` — 10-char team identifier

**Will be done when unblocked:**
- `tauri.conf.json` add `bundle.macOS.signingIdentity` + `providerShortName`
- GitHub Actions release workflow with the 4 secrets
- Notarize via `xcrun notarytool submit --wait`
- Staple ticket via `xcrun stapler staple`

**Do not start P5.3 until all 4 values are in user's `.env.release`.**

---

## External dependency summary

| 需要 | 用于 | 谁 | 今晚必须? |
|---|---|---|---|
| PNG ≥ 1024×1024 | P5.1 icon | 你 | 否,缺则跳 P5.1 |
| Sentry DSN | P5.5 激活(可空) | 你 | 否,空 DSN 代码仍落地 |
| Apple Developer $99/年 | P5.3 | 你 | **否,今晚不做 P5.3** |
| Azure Speech Key | Phase 4 (见 phase4 spec) | 你 | 代码落地不需要,真机验证需要 |
