# Phase 4 Sections — 实时语音面试 (Azure Speech)

Phase 4 flips the interview from "type" to "speak + type". We integrate
Azure Speech Services F0 (free tier) via its Python streaming SDK;
audio is captured in the desktop WebView with MediaRecorder, streamed
over the existing WebSocket as binary frames, and the backend forwards
each chunk to an ASR backend. Live partial transcripts stream back to
the client as they arrive; when the user stops speaking (VAD on Azure
side) the final transcript becomes the answer text for the turn.

All Phase 3 + 3.5 hard constraints still apply (A1 no key leaks extended
to ASR key, A2 WS first-frame, A3 TaskGroup cleanup including ASR
tasks). ASR is **not** BYOK per-request: Azure expects
constructor-time key/region and the key belongs to the user's local
machine (single-user app), so it lives in `.env` — never logged, never
echoed, never persisted in DB.

## Product decisions (locked)

| # | 决策项 | 值 |
|---|---|---|
| 1 | ASR provider | Azure Speech Services (F0 free tier, 5 hours/month) |
| 2 | ASR key 投放点 | 服务端 `.env` (`AZURE_SPEECH_KEY` + `AZURE_SPEECH_REGION`)。不走前端 header 因为 Azure SDK 是构造期注入 + 单机单用户场景够安全 |
| 3 | 默认模式 | 语音优先;文字 textarea 保留,可切换 |
| 4 | 采集路径 | WebView `MediaRecorder(audio/webm;codecs=opus)`,不走 Rust cpal,省很多 plumbing |
| 5 | 音频帧上行 | WS 二进制帧(`client.audio.chunk` 走 binary),首帧仍需 `client.session.init` 文本帧初始化 |
| 6 | 语音段结束检测 | Azure SDK `Recognized` event(自带 endpointing),前端不做 VAD |
| 7 | 字幕显示 | 前端区分 `partial`(灰色实时) 和 `final`(黑色 commit) 两层 |

## Execution order

| # | Section | Deps | Commit prefix |
|---|---|---|---|
| 1 | **P4.1 ASR infra** | — | `feat(asr): abstraction + Azure backend + mock` |
| 2 | **P4.2 WS audio protocol** | P4.1 | `feat(ws): binary audio frames + transcript events` |
| 3 | **P4.3 Runtime audio pipeline** | P4.2 | `feat(orchestrator): streaming audio → ASR → turn answer` |
| 4 | **P4.4 Desktop mic permission + capture** | — | `feat(desktop): microphone capture via MediaRecorder` |
| 5 | **P4.5 InterviewPage voice UX** | P4.3 + P4.4 | `feat(desktop): voice interview UI (hold-to-talk + live caption)` |
| 6 | **P4.6 Settings voice toggle** | P4.5 | `feat(desktop): voice/text mode toggle in settings` |
| 7 | **P4.X Test sweep + E2E** | 1–6 | `test: phase 4 integration and smoke sweep` |

---

## P4.1 — ASR infra

**Files (apps/api/):**
- `app/infra/asr/__init__.py` — public exports (`ASRBackend`, `ASRConfig`, `build_asr_backend`, typed errors)
- `app/infra/asr/config.py` — `ASRConfig(subscription_key: SecretStr, region: str)` frozen + masked repr (same pattern as LLMConfig)
- `app/infra/asr/errors.py` — `ASRError / ASRAuthError / ASRNetworkError / ASRUnsupportedAudioError`
- `app/infra/asr/base.py` — `ASRBackend` ABC with:
  ```python
  async def start_stream(self) -> None
  async def push_audio(self, chunk: bytes) -> None
  async def stop_stream(self) -> None
  def on_partial(self, callback: Callable[[str], None]) -> None
  def on_final(self, callback: Callable[[str], None]) -> None
  ```
- `app/infra/asr/azure_backend.py` — `AzureASRBackend` using `azure-cognitiveservices-speech` SDK;
  streaming PushAudioInputStream, event-driven recognized/recognizing handlers;
  chunks come in as raw bytes, Azure handles the decoding + endpointing
- `app/infra/asr/mock_backend.py` — `MockASRBackend` for tests: records pushed chunks, emits configurable partial + final transcripts on demand
- `app/infra/asr/factory.py` — `build_asr_backend(config) -> ASRBackend`; reads `AZURE_SPEECH_*` env for Azure; tests get the mock directly
- `app/infra/config.py` — add `azure_speech_key: str = ""`, `azure_speech_region: str = ""` (empty defaults so tests don't require them)
- `app/infra/logging.py` — already safe (structlog doesn't auto-log arbitrary kwargs) but add an explicit leak-prevention doc comment

**Tests (`tests/infra/test_asr.py`, 6 cases):**
1. `ASRConfig.__repr__` masks subscription_key
2. `build_asr_backend` returns AzureASRBackend for Azure config
3. MockASRBackend records chunks + fires callbacks
4. AzureASRBackend raises `ASRAuthError` on SDK auth error (mock `speech_recognizer` to throw)
5. AzureASRBackend stream lifecycle: start → push 3 chunks → stop doesn't hang
6. `grep_no_key` meta-test: `rg -n "subscription_key|AZURE_SPEECH_KEY"` only appears in config.py, factory.py, and azure_backend.py (no leakage)

**Deps to add:** `uv add "azure-cognitiveservices-speech>=1.40.0,<2"`

**Commit.** `feat(asr): abstraction + Azure backend + mock`

---

## P4.2 — WS audio protocol

**Files (apps/api/):**
- `app/ws/schemas.py` — add:
  - `ClientAudioStartEvent{event: "client.audio.start", turn_index: int}` (text frame)
  - `ClientAudioStopEvent{event: "client.audio.stop", turn_index: int}` (text frame)
  - `ServerTranscriptPartialEvent{event: "server.transcript.partial", turn_index, text}` (outbound)
  - `ServerTranscriptFinalEvent{event: "server.transcript.final", turn_index, text}` (outbound, the final becomes the turn's `answer`)
- `app/ws/endpoint.py`:
  - Remove the blanket "binary audio frames are reserved for ASR" rejection — binary frames now go to an active ASR stream
  - State machine: a WS connection is in `idle` (between turns) or `recording` (between `audio.start` and `audio.stop`)
  - Binary frame arrives when not recording → send `server.error{code:"audio_not_started"}` + continue (don't close)
  - Text `audio.start` → allocate ASR backend (per-turn) + register partial/final callbacks → push `server.transcript.partial/final` into the runtime queue
  - Text `audio.stop` → call `backend.stop_stream()` (may still emit a final after the last chunk) + drain
- `app/orchestrator/events.py` — add `TranscriptPartialEvent`, `TranscriptFinalEvent`
- `app/orchestrator/runtime.py` — `start_audio_turn` / `push_audio` / `stop_audio_turn` helpers that wrap an ASR backend instance; register callbacks that enqueue events onto `event_queue`; stash the latest `final` text in a dict so the handler can convert it to the turn's `answer` when `client.turn.end` fires
- `tests/test_ws.py` — 4 new cases:
  1. Binary frame outside recording → `server.error{code:"audio_not_started"}` (not close)
  2. `audio.start` → push 2 binary chunks → `audio.stop` → transcript.final emitted with mock text
  3. `audio.start` → `audio.stop` without chunks → final empty, no crash
  4. `audio.start` twice without stop → second one ignored with `server.error{code:"audio_already_started"}`

**Commit.** `feat(ws): binary audio frames + transcript events`

---

## P4.3 — Runtime audio pipeline

**Files (apps/api/):**
- `app/orchestrator/runtime.py`:
  - Add `_asr_backend: ASRBackend | None` + `_current_audio_turn: int | None`
  - `async def start_audio_turn(turn_index, backend_factory)` — constructs backend from factory, registers callbacks that put events onto `event_queue`, stores last final text per turn in `_last_final_by_turn: dict[int, str]`
  - `async def push_audio(chunk: bytes)` — guard: backend must be running; else raise `SessionClosedError`-like typed error
  - `async def stop_audio_turn()` — stops backend, waits for trailing final (max 2s), returns
  - `get_audio_answer(turn_index) -> str | None` — called by `client.turn.end` handler to grab the final text
  - `on_session_end()` — also cancel any running ASR backend and clear `_last_final_by_turn`
- `app/ws/endpoint.py` — when `client.turn.end` arrives and the user was in voice mode (audio.start happened), resolve `answer` via `runtime.get_audio_answer(turn_index)` instead of the client-supplied `answer` field (which may be empty in voice mode)
- Backend factory plumbing: the WS endpoint reads Azure env on startup and passes a factory lambda into runtime so runtime stays decoupled from `infra/asr/config.py`

**Tests (`tests/orchestrator/test_audio_pipeline.py`, 4 cases):**
1. `start_audio_turn` → push 2 chunks → stop → final event on queue, `get_audio_answer` returns final text
2. `start_audio_turn` → `on_session_end` cancels running backend (backend's `stop_stream` called)
3. Weakref extension of runtime cleanup test (already exists): ASR backend also released after `on_session_end`
4. Two consecutive turns with audio: turn 1 final doesn't leak into turn 2

**Commit.** `feat(orchestrator): streaming audio → ASR → turn answer`

---

## P4.4 — Desktop mic permission + capture

**Files:**
- `apps/desktop/src-tauri/Info.plist` (may need creation) — add `NSMicrophoneUsageDescription` with Chinese copy "Eatit 需要使用麦克风来进行语音面试"
- `apps/desktop/src-tauri/tauri.conf.json` — ensure webview permits media capture (usually default, confirm)
- `apps/desktop/src/lib/mic.ts` — new:
  - `requestMicPermission()` — calls `navigator.mediaDevices.getUserMedia({audio:true})`, catches errors, returns typed result
  - `createAudioRecorder(onChunk: (chunk: Blob) => void, onFinal: () => void)` — wraps `MediaRecorder` with 100ms timeslice; produces Blob chunks
- No new React UI yet (that's P4.5); this section just makes the capture primitive + tests

**Tests:**
- Frontend tests use Vitest if already configured, else lint-only. Realistically skip unit tests for mic (hard to mock WebView APIs cleanly) and cover via the P4.X E2E. Keep this section light.
- `grep -n "getUserMedia" apps/desktop/src/lib/mic.ts` — exists.

**Manual verification (in commit body):** open tauri dev, call `requestMicPermission()` from devtools, OS permission prompt appears.

**Commit.** `feat(desktop): microphone capture via MediaRecorder`

---

## P4.5 — InterviewPage voice UX

**Files (apps/desktop/src/):**
- `pages/interview/VoiceControl.tsx` — new:
  - "按住说话" button (press-and-hold; `onMouseDown`/`onTouchStart` starts recording, `onMouseUp`/`onTouchEnd`/`onBlur`/`onMouseLeave` stops — swap to toggle mode if it proves buggy)
  - While recording: pulsing red dot + "正在聆听..." + current partial transcript inline
  - Recording state machine lives in XState alongside the interview machine (or as a child machine — easier: flat boolean `isRecording` + refs)
- `statecharts/interview-machine.ts` — add states / events for voice:
  - events: `AUDIO_START`, `AUDIO_STOP`, `TRANSCRIPT_PARTIAL`, `TRANSCRIPT_FINAL`
  - context additions: `partialTranscript: string`, `finalTranscript: string`
  - `user_answering` state owns these — final transcript replaces `draftAnswer` automatically
- `pages/InterviewPage.tsx`:
  - On `AUDIO_START`: send `{event:"client.audio.start", turn_index}` text frame
  - During recording: pipe each chunk Blob → `arrayBuffer()` → `socket.send(buffer)` (binary)
  - On `AUDIO_STOP`: send `{event:"client.audio.stop", turn_index}`
  - Handle `server.transcript.partial/final` events from the existing onmessage handler → dispatch to machine
  - Keep the existing textarea; add a mode toggle "语音 / 文字" at the top of the answer area
  - On submit: if voice mode, answer comes from `finalTranscript`; if text mode, from textarea (existing behavior)
- `pages/interview/LiveCaption.tsx` — simple component rendering partial (gray) + final (black) transcript, autoscroll

**Acceptance:**
- `pnpm exec tsc --noEmit` + `pnpm lint` clean
- `grep -n "client.audio.start\|server.transcript.final" apps/desktop/src/pages/InterviewPage.tsx` — both hit

**Commit.** `feat(desktop): voice interview UI (hold-to-talk + live caption)`

---

## P4.6 — Settings voice toggle

**Files (apps/desktop/src/):**
- `pages/SettingsPage.tsx` — in the "面试体验" section (next to the observer toggle), add:
  - "面试语音模式" switch: `voice` / `text`;  persisted via a new `app_settings` key `interview_input_mode`
  - When Azure env not configured on backend, show "⚠️ 服务端未配置 Azure Speech,语音模式不可用" with a link to `/settings`'s BYOK section (well, Azure is backend env, so the message is just informational — maybe point the user to README)
- `app/domain/settings/service.py` — add `interview_input_mode` to `ALLOWED_KEYS` (values `"voice"` or `"text"`, default `"voice"`)
- `tests/domain/test_app_settings.py` — extend parameterization with `interview_input_mode` x 2 values
- `pages/InterviewPage.tsx` — read `interview_input_mode` at mount; if `text`, hide VoiceControl; if `voice` but ASR unavailable (backend 400s on `audio.start`), fall back to text with a banner

**New backend health endpoint for ASR availability check:** `GET /api/v1/asr/health` returns `{available: bool, provider: "azure"}`. Frontend uses this to disable voice UI if Azure env missing.

**Commit.** `feat(desktop): voice/text mode toggle in settings`

---

## P4.X — Test sweep + E2E

Standard sweep. Additional coverage:
- WS E2E: session.init → audio.start → 3 chunks → audio.stop → transcript.final → turn.end → question.generated (mock ASR + mock LLM)
- `rg -n "AZURE_SPEECH_KEY" apps/api/app/` — only appears in config.py, factory.py, azure_backend.py (no leak into logs / tests / errors)

All four gates (pytest / tsc / lint / cargo check) green.

**Commit.** `test: phase 4 integration and smoke sweep`

---

## External dependency user must satisfy before verification

1. **Azure Speech F0 resource** — user creates on portal.azure.com, picks region (e.g. `eastasia`), copies Key 1 + Region into `.env`:
   ```
   AZURE_SPEECH_KEY=...
   AZURE_SPEECH_REGION=eastasia
   ```
2. **macOS microphone permission** — granted at first `getUserMedia()` call, handled gracefully if denied.

Until #1 is supplied, Ralph's code runs against the mock backend only; all tests green; real audio end-to-end waits for user.
