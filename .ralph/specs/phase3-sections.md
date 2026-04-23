# Phase 3 Sections — Per-Section Spec

Ralph reads the anchor for the section it picked from `fix_plan.md`.
Each section below has the same shape:

- **Goal** — one sentence
- **Deps** — other sections that must already be `[x]`
- **Files** — exhaustive list of files to create / modify
- **Key interfaces / logic** — the non-obvious parts that are easy to
  get wrong; contract-level, not line-by-line code
- **Acceptance** — commands to run; ALL must pass, copy their concise
  output into the commit body
- **Commit** — the exact Conventional Commits prefix to use

---

## P3.9 SettingsPage

**Goal.** A real Settings page where the user chooses an LLM provider,
pastes a key, optionally adjusts base URL and model, and hits "测试连接"
to verify the round-trip works. Also a "数据管理" zone that exposes the
local data directory and a destructive "清空本地数据" button.

**Deps.** P3.1 (LLM test endpoint), P3.7 (keychain commands) — both already done.

**Files (all under apps/desktop/src/):**
- `pages/SettingsPage.tsx` — real body (replace placeholder stub)
- `pages/settings/ProviderSelect.tsx` — new; dropdown of the 6 supported
  providers + "自定义 (OpenAI 兼容)" with built-in base URL presets
- `pages/settings/KeyInput.tsx` — new; masked input with show/hide and
  live display via `maskApiKey()`
- `pages/settings/TestConnectionButton.tsx` — new; calls
  `POST /api/v1/llm/test` with the header from
  `encodeForHeader(config)` and renders `{ok, usage.{prompt_tokens,
  completion_tokens, latency_ms}}` or the error_code/error_message
- `pages/settings/DataManagement.tsx` — new; shows the local data path
  (read from Tauri `path.appLocalDataDir` or fall back to "项目 .data/"
  when running dev), "导出" (stub, post-Phase-3 ok), "清空本地数据"
  button with a confirm dialog
- `lib/llm/providers.ts` — new; static list of providers with
  registration URL + preset base_url + suggested model(s)
- `api/llm.ts` — new; thin client for `POST /api/v1/llm/test`

**Key interfaces / logic:**
- Provider registry (in `providers.ts`):
  ```ts
  export const PROVIDERS = [
    { id: "siliconflow", label: "硅基流动", registerUrl: "https://cloud.siliconflow.cn/i/PLACEHOLDER", baseUrl: "https://api.siliconflow.cn/v1", models: ["Qwen/Qwen2.5-7B-Instruct", ...] },
    { id: "deepseek", label: "DeepSeek", registerUrl: "https://platform.deepseek.com/", baseUrl: "https://api.deepseek.com/v1", models: ["deepseek-chat"] },
    { id: "dashscope", label: "阿里云百炼", ... },
    { id: "openai", label: "OpenAI", ... },
    { id: "anthropic", label: "Anthropic", ... },
    { id: "custom", label: "自定义 (OpenAI 兼容)", baseUrl: "", models: [] },
  ] as const;
  ```
- "测试连接" flow:
  1. Build the LLMConfig from the form
  2. Call `saveLLMConfig(config)` (keychain write) — gives the user an
     eager save
  3. POST to `http://127.0.0.1:8000/api/v1/llm/test` with header
     `X-LLM-Config: <encodeForHeader(config)>`
  4. Render the returned `LLMTestResponse` as a success tag
     (tokens + latency) or a red error box showing error_code +
     error_message. Do NOT surface the key in the error zone.
- "清空本地数据" confirm flow: show a shadcn Dialog asking "确定清空?"
  Once confirmed, call `deleteLLMConfig()` AND trigger a (new) backend
  endpoint `POST /api/v1/local/wipe` — **defer this endpoint to a
  follow-up; in this section just wire the keychain delete and a
  "功能建设中" toast for the wipe**.

**Acceptance:**
1. From `apps/desktop/`:
   - `corepack pnpm exec tsc --noEmit` → clean
   - `corepack pnpm lint` → clean
2. From `apps/api/`:
   - `uv run pytest -v` → still green (no regression; this section is
     frontend-only)
3. Manual sanity (record in commit body as text, no screenshot required):
   - `grep -rn "sk-" apps/desktop/src/` → no hard-coded sample keys
   - `grep -rn "api.openai.com\|api.deepseek.com\|api.anthropic.com" apps/desktop/src/` → only in
     `lib/llm/providers.ts` (and only as provider metadata, never for
     `fetch`).

**Commit.** `feat(desktop): settings page with BYOK provider + test connection`

---

## P3.8 OnboardingPage

**Goal.** A 4-step first-run wizard: 欢迎 → LLM 配置 → 上传第一份资料
(可跳过) → 完成. Completion is persisted by writing
`onboarding_completed_at` via the backend settings API. On app launch,
if `onboarding_completed_at` is missing, auto-redirect to `/onboarding`
before the AppShell renders.

**Deps.** P3.6 (app_settings table), P3.9 (shares the provider form).

**Files:**
- Backend (apps/api/):
  - `app/api/routes/app_settings.py` — new; `GET /api/v1/app-settings/{key}`
    and `PUT /api/v1/app-settings/{key}` using the existing service;
    whitelist enforced by the service
  - `app/api/router.py` — register the new router
  - `tests/api/test_app_settings_api.py` — new; 4 cases (GET missing →
    null, PUT then GET → value, PUT bad key → 400, PUT secret-shaped
    value → 400)
- Frontend (apps/desktop/src/):
  - `pages/OnboardingPage.tsx` — new; 4 steps, progress header
  - `pages/onboarding/StepWelcome.tsx`
  - `pages/onboarding/StepLLM.tsx` — reuse `ProviderSelect` + `KeyInput`
    from P3.9
  - `pages/onboarding/StepUpload.tsx` — drop-zone stub, "跳过" button
    works, implementation can be deferred to P3.10b
  - `pages/onboarding/StepDone.tsx` — triggers
    `PUT /api/v1/app-settings/onboarding_completed_at` with current ISO
    datetime, then navigates to `/`
  - `api/appSettings.ts` — new; TS client for GET/PUT
  - `routes/index.tsx` — add `/onboarding` route (OUTSIDE the AppShell
    layout, full-screen) and a guard that redirects on first launch
    when the setting is absent

**Key interfaces / logic:**
- `PUT` body: `{ value: <JSON-serializable> }` → store as JSON
- `GET` returns `{ value: ... }` or 404 with `{ detail: "not set" }`
- Full-screen wizard layout (no sidebar): render `<Outlet />` in a
  parent route element that does NOT include `AppShell`
- Redirect guard in a new component `components/OnboardingGate.tsx`
  wrapped around `<AppShell />` that queries
  `/api/v1/app-settings/onboarding_completed_at` via TanStack Query;
  while loading show a shimmer; if null → `<Navigate to="/onboarding" />`

**Acceptance:**
1. `apps/api/`:
   - `uv run pytest -v` → all green, new test file counted
2. `apps/desktop/`:
   - `corepack pnpm exec tsc --noEmit` → clean
   - `corepack pnpm lint` → clean
3. `grep -rn "onboarding_completed_at" apps/api/app/ apps/desktop/src/` — the
   string exists in exactly: the api route, the settings service's
   whitelist, the OnboardingPage's step 4, the gate.

**Commit.** `feat(onboarding): first-run wizard + app_settings REST`

---

## P3.3 Six Agents

**Goal.** Replace each agent service stub in `apps/api/app/agents/*/
service.py` with a real implementation that calls the relevant prompt
via Instructor and returns the agent's structured output. No
LangGraph wiring yet — that's P3.4.

**Deps.** P3.1 (gateway), P3.2 (prompts). Both done.

**Files (all under apps/api/):**
- `app/infra/llm/instructor_client.py` — new; helper that builds a
  patched Instructor client around the gateway's `complete` method so
  each agent can call `client.chat.completions.create(response_model=X, ...)`
  — see implementation note below
- `app/agents/parse/schemas.py` — already exists from Phase 2; reconcile
  with `tests/test_assets_api.py` (may need minor tweaks)
- `app/agents/parse/service.py` — real `async def run(input, gateway) -> ParseAgentOutput`
- `app/agents/framework/{schemas,service}.py` — same shape; schema lines
  up with the System prompt output fields in
  `app/prompts/framework/system.j2`
- `app/agents/interviewer/{schemas,service}.py`
- `app/agents/reference/{schemas,service}.py`
- `app/agents/compression/{schemas,service}.py`
  - Enforce a **3s timeout** via `asyncio.wait_for` wrapping the call.
    On timeout, return a degraded summary constructed from the last
    two turns (no LLM call) with `preserved_keywords=[]` and
    `open_threads=[]`.
- `app/agents/report/{schemas,service}.py`
  - Output schema must include `pass_probability: int = Field(ge=0, le=100)`,
    `reasons: list[Reason]`, `next_actions: list[str]`
- Tests — for each agent, one test file under `tests/agents/test_<agent>.py`
  with 3 cases:
  1. Happy path — mock gateway returns a well-formed response → agent
     returns the expected Pydantic model
  2. Instructor retry — first call returns malformed JSON, second call
     returns valid → agent returns the valid one (use
     `monkeypatch` on the gateway's `complete`)
  3. Timeout (for Compression) or network error (for others) — gateway
     raises `LLMNetworkError` → agent raises or returns a typed
     degraded output (spec it per agent; be explicit in the commit)

**Key interfaces / logic:**
- Instructor helper (`instructor_client.py`):
  ```python
  import instructor
  import litellm

  def patched_acompletion(gateway):
      async def _call(**kwargs):
          # strip Instructor-specific kwargs if needed; then:
          return await gateway.complete(messages=kwargs["messages"], **{k:v for k,v in kwargs.items() if k != "messages"})
      return _call

  def make_instructor(gateway) -> instructor.AsyncInstructor:
      return instructor.from_litellm(litellm.acompletion)  # or wrapped via gateway
  ```
  Pick whichever integration path actually works against the installed
  `instructor` version. Verify with a smoke test before relying on it.
- All agents share this shape:
  ```python
  async def run(self, input: InModel, gateway: LLMGateway) -> OutModel:
      system = render_prompt("<agent>", "system")
      user = render_prompt("<agent>", "user", **input.model_dump())
      client = make_instructor(gateway)
      return await client.chat.completions.create(
          messages=[{"role":"system","content":system}, {"role":"user","content":user}],
          response_model=OutModel,
          max_retries=2,
      )
  ```

**Acceptance:**
1. `apps/api/` — `uv run pytest -v`:
   - All prior tests still green
   - 6 new test files × 3 cases = 18 new cases green
2. `uv run python -c "from app.agents.report.service import ReportAgentService; import inspect; print(inspect.signature(ReportAgentService().run))"` shows `(input, gateway)` signature
3. `grep -n "pass_probability" apps/api/app/agents/report/schemas.py` — field exists with ge=0 le=100

**Commit.** `feat(agents): six agents on instructor + gateway`

---

## P3.4 LangGraph orchestrator

**Goal.** Build `SessionRuntime` + `turn_graph` that orchestrates
per-turn agent work (parallel `turn_assessment || compression`, then
`next_question`), with asyncio TaskGroup memory discipline and an
explicit `on_session_end()` lifecycle hook. Reference answer generation
runs as a separate independent async task spawned per turn.

**Deps.** P3.3 (all agents callable).

**Files (apps/api/):**
- `app/orchestrator/runtime.py` — `SessionRuntime` class
- `app/orchestrator/turn_graph.py` — the LangGraph `StateGraph` factory
- `app/orchestrator/state.py` — `TurnState` Pydantic model (not a dataclass — Instructor friendly)
- `app/orchestrator/events.py` — outbound WS event dataclasses (if not
  already defined in `app/ws/schemas.py`)
- Tests:
  - `tests/orchestrator/test_runtime_cleanup.py` — weakref + gc
    assertion for A3 constraint
  - `tests/orchestrator/test_turn_graph.py` — happy path with mock
    gateways for Interviewer, Framework, Compression
  - `tests/orchestrator/test_compression_timeout.py` — compression
    exceeds 3s → degraded summary path taken

**Key interfaces / logic:**
- `SessionRuntime`:
  ```python
  class SessionRuntime:
      def __init__(self, session_id: str, llm_config: LLMConfig):
          self.session_id = session_id
          self._llm_config: LLMConfig | None = llm_config
          self._task_group: asyncio.TaskGroup | None = None
          self._event_queue: asyncio.Queue = asyncio.Queue()
          self._ref_answer_tasks: set[asyncio.Task] = set()

      async def __aenter__(self): ...
      async def __aexit__(self, *exc): await self.on_session_end()

      async def run_turn(self, question: str, answer: str) -> TurnResult: ...

      async def on_session_end(self) -> None:
          # cancel all subtasks, then null out config
          for t in self._ref_answer_tasks: t.cancel()
          self._ref_answer_tasks.clear()
          if self._task_group is not None:
              # TaskGroup cancels on exit; nothing extra to do if already inside
              pass
          self._llm_config = None
          while not self._event_queue.empty(): self._event_queue.get_nowait()
  ```
- `turn_graph`: LangGraph StateGraph with nodes
  `turn_assessment`, `compression`, `next_question`. Edges:
  `START -> [turn_assessment, compression] -> next_question -> END`.
  Compression node wraps its agent call in `asyncio.wait_for(..., 3.0)`
  with fallback to a degraded summary node.
- Reference answer task: fire-and-forget started from `run_turn`;
  registered on `self._ref_answer_tasks`; its result is pushed to the
  event queue as `server.turn.reference_answer_ready`.

**Acceptance:**
1. `apps/api/` — `uv run pytest -v` new tests green, nothing else regresses
2. `tests/orchestrator/test_runtime_cleanup.py` specifically asserts:
   ```python
   ref = weakref.ref(runtime._llm_config)
   await runtime.on_session_end()
   gc.collect()
   assert ref() is None
   ```
3. `grep -n "asyncio.TaskGroup\|on_session_end" apps/api/app/orchestrator/runtime.py` — both present

**Commit.** `feat(orchestrator): langgraph turn_graph with task group cleanup`

---

## P3.5 REST/WS real

**Goal.** Replace Phase 2 mock bodies with real orchestration:
- `POST /api/v1/assets/{id}/parse` → ParseAgent
- `POST /api/v1/sessions` → FrameworkAgent
- `POST /api/v1/sessions/{id}/report` → TaskQueue job that runs ReportAgent
- WS `/ws/sessions/{session_id}` — enforce `client.session.init`
  first-frame protocol, wire `client.turn.end` to
  `SessionRuntime.run_turn`, push all events to the client

**Deps.** P3.4.

**Files (apps/api/):**
- `app/api/routes/assets.py` — parse route switches from mock to real
- `app/api/routes/sessions.py` — create_session + trigger_report bodies
  rewritten
- `app/ws/schemas.py` — add `client.session.init` event
- `app/ws/<new or existing>.py` — the WS handler: on connect, await the
  first frame, require it to be `client.session.init`, otherwise
  `server.error{code:"session_not_initialized"}` + close; on
  `client.turn.end` call `SessionRuntime.run_turn` and relay events
- `tests/test_ws.py` — update to cover the first-frame protocol + happy
  path + wrong-first-event rejection
- `tests/test_assets_api.py` — monkeypatch the agent to assert the real
  path runs instead of the mock
- `tests/test_reports_api.py` — similar

**Key interfaces / logic:**
- `client.session.init` payload: `{event: "client.session.init", config: LLMConfigPayload}`.
  On receipt: validate via Pydantic, build `SessionRuntime` with the
  config, enter its context manager, store it keyed by session_id on
  the WS consumer.
- Any other event received before init → send
  `server.error{code:"session_not_initialized"}` then close (1008
  policy violation).
- On WS close / disconnect: `await runtime.on_session_end()` from a
  `finally` block.
- `POST /api/v1/sessions/{id}/report` wraps ReportAgent in a TaskQueue
  job (the asyncio backend already shipped in Phase 2.5); the route
  returns 202 + a task id; a follow-up `GET` pollable endpoint can be
  minimal / stub-return for Phase 3 purposes.

**Acceptance:**
1. `apps/api/` — `uv run pytest -v` green (includes updated mock
   assertions)
2. `rg -n "not_implemented|TODO: wire" apps/api/app/ws/ apps/api/app/api/routes/` — 0 hits
3. WS-specific: the updated `tests/test_ws.py` includes a
   `test_websocket_rejects_wrong_first_event` case that asserts the
   `server.error{code:"session_not_initialized"}` shape.

**Commit.** `feat(api): wire real agents to REST and WebSocket endpoints`

---

## P3.10b UploadPage + ConfigPage

**Goal.** Real bodies for the 上传与解析 and 面试配置 pages.

**Deps.** P3.5.

**Files (apps/desktop/src/):**
- `pages/UploadPage.tsx` — drop-zones for resume + JD (pdf/doc/docx/txt),
  calls `POST /api/v1/assets` on upload, then shows parse result card
  from `POST /api/v1/assets/{id}/parse`
- `pages/upload/DropZone.tsx`
- `pages/upload/ParseResultCard.tsx`
- `pages/ConfigPage.tsx` — 3 radio tile groups (level / style / duration)
  using the design `.tile` pattern → on "开始面试" calls `POST /api/v1/sessions`
  and navigates to `/interview/<session_id>`
- `api/assets.ts` / `api/sessions.ts` — extend with the parse + create
  calls if not already present
- `stores/app-store.ts` — add slice for current-upload and current-config
  (use zustand convention already present)

**Key interfaces / logic:**
- Upload uses `multipart/form-data` with 2 fields `resume_file` and
  `jd_file`. Files are sent with `X-LLM-Config` header so the parse
  sub-call (server-side) can use the user's gateway.
- "开始面试" is disabled until both resume + jd parsed successfully.

**Acceptance:**
1. `apps/desktop/` — `corepack pnpm exec tsc --noEmit` + `corepack pnpm lint` clean
2. `apps/api/` — pytest unchanged (no backend changes in this section)
3. Manual: on navigation from Config → Interview, the URL contains the
   real session_id from the POST response (verified via a tiny
   frontend test or at least `grep -n "navigate.*session_id" apps/desktop/src/pages/ConfigPage.tsx`).

**Commit.** `feat(desktop): upload and config pages`

---

## P3.10c InterviewPage + HistoryPage + ReportPage

**Goal.** Real bodies for 实时面试 / 面试记录 / 评估报告.

**Deps.** P3.5 (backend), P3.10b (upload+config).

**Files (apps/desktop/src/):**
- `pages/InterviewPage.tsx` — XState-driven view; opens WS, sends
  `client.session.init` as first frame, then `client.turn.start` /
  `client.turn.end` per turn; receives `server.*` events and updates
  the state machine
- `statecharts/interview-machine.ts` — existing file; rewrite as:
  `idle → connecting → ready → user_answering → scoring → next_question → ended`
  with transitions triggered by WS events; on `ended`, navigate to
  `/report/<session_id>`
- `pages/HistoryPage.tsx` — list sessions from `GET /api/v1/sessions`
  (use the existing endpoint), clicking a row goes to `/report/<id>`
- `pages/ReportPage.tsx` — shows `pass_probability` (0..100 circle or
  bar), `summary`, `reasons` (each row: aspect / verdict tag /
  quote with evidence-turn anchor), `next_actions`; while report is
  still generating, show a skeleton screen + 文案 "通常约 20 秒"
- `pages/report/ReasonRow.tsx`, `pages/report/PassProbabilityRing.tsx`

**Key interfaces / logic:**
- WS wrapper uses the helper at `apps/desktop/src/api/ws.ts` (or
  create one). First frame goes out only after the socket `onopen`
  event fires.
- The URL is `ws://127.0.0.1:8000/ws/sessions/<session_id>?token=mock`.
- Report skeleton: `<div className="shimmer" />` (there's no shimmer
  utility yet — add one via the design tokens; 1.4s loop).

**Acceptance:**
1. `apps/desktop/` — `corepack pnpm exec tsc --noEmit` + `corepack pnpm lint` clean
2. `corepack pnpm build` succeeds
3. `grep -n "pass_probability\|next_actions" apps/desktop/src/pages/ReportPage.tsx` — both present
4. `grep -n "client.session.init" apps/desktop/src/` — at least one hit in the
   InterviewPage WS wiring

**Commit.** `feat(desktop): interview/history/report with xstate and ws`

---

## P3.12 Test sweep + end-to-end smoke

**Goal.** Final tidy. Fill obvious test gaps, run the full matrix,
demonstrate a full end-to-end dry run with mock gateway.

**Deps.** All prior sections `[x]`.

**Files:**
- Review each agent test file; fill in any TODO-level case you skipped
  (malformed JSON retry is the most likely hole).
- `tests/e2e/test_end_to_end_mock.py` — new; spins up `TestClient`,
  seeds an asset, calls parse → create session → WS connect + init →
  3 turns → request report → poll → assert all fields in the report
  response. Use an in-process mock gateway.

**Acceptance:**
1. `apps/api/`:
   - `uv run pytest -v` — every test in the suite green, no xfail
     markers added during Phase 3 remain
2. `apps/desktop/`:
   - `corepack pnpm exec tsc --noEmit` green
   - `corepack pnpm lint` green
   - `corepack pnpm build` green (tsc + vite build)
3. `apps/desktop/src-tauri/`:
   - `source "$HOME/.cargo/env" && cargo check` green
4. Working tree is clean (`git status --porcelain` produces no lines).

**Commit.** `test: phase 3 integration and smoke sweep`

After this commit, and only if all four acceptance checks above pass,
set `EXIT_SIGNAL: true`.
