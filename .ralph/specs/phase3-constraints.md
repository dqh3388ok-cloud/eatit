# Phase 3 Hard Constraints (不可违反)

These are the architecture red lines carried over from the handoff
document. If any implementation step would violate one of these, stop
and report — do not proceed.

## A. Architecture

### A1 — Backend is the only LLM client

- Frontend keychain stores `LLMConfig` (done in P3.7).
- Frontend calls backend with `X-LLM-Config` HTTP header (base64 JSON).
- Backend middleware parses header → `request.state.llm_config`
  (done in P3.1).
- **Frontend never talks to third-party LLM vendors directly.**
  Specifically: no `fetch("https://api.openai.com/...")` in
  `apps/desktop/src/` under any circumstances. The test endpoint that
  the Settings page calls is `POST /api/v1/llm/test` on the local
  backend — the backend relays to LiteLLM.
- **`api_key` must never appear in**:
  - Python logs (stdout, structlog events, Sentry context)
  - Database columns or JSON blobs
  - Cache keys
  - Error responses echoed back to the client
  - Commit messages, code comments, documentation samples

### A2 — WebSocket first-frame protocol

- Route is `/ws/sessions/{session_id}`.
- The client's FIRST message after connection MUST be a
  `client.session.init` event carrying LLMConfig.
- Backend stores LLMConfig on the session runtime only for the
  lifetime of the WS connection.
- If any other event type arrives before `client.session.init`,
  respond with `server.error{code:"session_not_initialized"}` and
  close the socket.

### A3 — Orchestrator memory cleanup

- `SessionRuntime` (new in P3.4) manages all in-flight work via
  `asyncio.TaskGroup`.
- Provides `async def on_session_end(self) -> None` that:
  1. Cancels the TaskGroup cleanly.
  2. Sets `self.llm_config = None` and clears any other field holding
     the config or the gateway.
  3. Clears the outbound event queue.
- Must be invoked from at least three paths: WS close, explicit
  `client.session.end`, uncaught exception in the runtime.
- Has a test that holds a weakref to the LLMConfig before
  `on_session_end()`, calls it, runs `gc.collect()`, asserts the
  weakref is dead.

### A4 — Report schema hard fields

The Report agent's output and the corresponding API response include:
- `pass_probability: int` — 0..100 inclusive
- `reasons: list[{aspect: str, verdict: Literal["strong","solid","mixed","weak"], evidence_turn_index: int, quote: str}]`
- `next_actions: list[str]`

Missing any of these = acceptance failure.

## B. Engineering discipline

1. **One commit per section.** Conventional Commits prefix as
   specified in `phase3-sections.md` per section.
2. **Full errors surfaced.** When a verification command fails, show
   the complete error message. No `--no-verify`, `pytest -x --lf`
   silencing, or try/except catch-all that swallows.
3. **No placeholder implementations.** If a section's acceptance says
   "Instructor enforces JSON", a stub that returns `{}` doesn't count.
4. **Relative paths only.** `/Users/...` must not appear in source,
   tests, or documentation. Use `~/` or repo-relative paths.
5. **No remote push.** Ralph commits locally. Pushing is the user's
   call.
6. **`.ralph/` and `.ralphrc` are protected.** Never modify or delete.

## C. Secrets hygiene

- `LLMConfig` has `api_key: SecretStr`. Retrieve only via
  `config.api_key.get_secret_value()` at the exact call site that
  hands it to LiteLLM. Do not pass it through intermediate structures.
- When logging a request, log: method, path, status, duration.
  Never log headers in bulk. Specifically filter out `X-LLM-Config`
  if a header log is needed.
- `app_settings` table MUST NOT accept keys or values that match the
  secret blocklist regex defined in
  `apps/api/app/domain/settings/service.py` (already enforced).

## D. Style

- Python: ruff line-length 100, target py311, existing style.
- TypeScript: existing Prettier config, strict type checking (no
  `any` unless absolutely forced — justify in the commit body).
- CSS: use the design tokens declared in
  `apps/desktop/src/index.css` (`--brand`, `--ink-*`, `--r-*`, etc.).
  Don't inline random hex colors.
- Chinese UI copy. English identifiers + comments. Technical terms
  that are already Chinese in the PRD (e.g. "面试官") stay Chinese.
