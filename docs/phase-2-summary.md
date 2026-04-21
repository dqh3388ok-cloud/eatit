# Phase 2 Summary

## Scope

Phase 2 established the persistence layer, API contracts, and websocket protocol skeleton for Eatit without connecting any real LLM orchestration. The backend already writes to PostgreSQL, exposes typed REST responses, validates websocket events, and keeps all session- and asset-level queries scoped to a fixed mock user.

## Models

- `app/models/base.py`
  - `Base`: shared SQLAlchemy declarative base with async support.
  - `UUIDv7PrimaryKeyMixin`: gives every table an application-generated UUIDv7 primary key.
  - `TimestampMixin`: gives every table `created_at` and `updated_at` columns with server defaults.
- `app/models/enums.py`
  - `CandidateAssetStatus`: lifecycle of the resume/JD asset bundle.
  - `ParseResultStatus`: state of the parse output record.
  - `InterviewStyle`: interview tone/style enum for the config snapshot.
  - `InterviewDirection`: interview direction enum for the config snapshot.
  - `InterviewSessionStatus`: high-level interview state machine status.
  - `InterviewReportStatus`: report generation lifecycle enum.
- `app/models/user.py`
  - `User`: minimal user record used by the mock auth dependency and ownership filtering.
- `app/models/asset.py`
  - `CandidateAsset`: owns resume/JD references, upload metadata, and the current asset status.
  - `ParseResult`: stores the parse JSON payload and match summary for one asset bundle.
- `app/models/session.py`
  - `InterviewSession`: root interview session record tied to a user and candidate asset.
  - `InterviewConfig`: normalized snapshot of style/direction/duration for one session.
  - `DirectionFramework`: JSONB storage for the framework returned at session creation time.
  - `InterviewTurn`: one interview round with question/answer text fields.
  - `TurnAssessment`: JSONB-backed single-turn assessment payload.
  - `CompressedTurnSummary`: JSONB-backed compressed memory for one turn plus session link.
- `app/models/report.py`
  - `InterviewReport`: final report record with status timestamps and JSONB payload.

## Schemas

- `app/schemas/common.py`
  - `SchemaModel`: base Pydantic config used by all API and protocol schemas.
  - `TimestampedResponse`: shared `id/created_at/updated_at` response wrapper.
  - `PaginatedResponse[T]`: generic pagination envelope for list endpoints.
- `app/schemas/frameworks.py`
  - `FrameworkStage`: one stage in the generated interview framework.
  - `DirectionFramework`: structured framework returned when creating a session.
- `app/schemas/turns.py`
  - `NormalizedQuestion`: normalized question shape for turn-level outputs.
  - `NormalizedAnswer`: normalized answer/transcript shape.
  - `NormalizedUserAssessment`: normalized per-turn assessment shape.
  - `CompressedTurnSummary`: compressed memory shape used by the websocket contract.
  - `ReferenceAnswer`: async reference answer payload shape.
- `app/schemas/parse.py`
  - `JobRequirement`: one parsed job requirement item.
  - `CandidateHighlight`: one parsed candidate highlight item.
  - `CandidateRisk`: one parsed candidate risk item.
  - `ProjectHook`: one parsed project hook item.
  - `ParseResultPayload`: PRD-aligned parse agent payload.
  - `ParseRequestResponse`: wrapper returned immediately after triggering parse.
  - `ParseResultResponse`: stored parse result response with timestamps.
  - `ParseResultPreview`: compact preview used when an asset summary is needed.
- `app/schemas/assets.py`
  - `AssetUploadRequest`: optional bundle id for appending files to an existing asset bundle.
  - `AssetUploadResponse`: typed response for resume/JD upload endpoints.
  - `CandidateAssetResponse`: asset bundle response with optional parse preview.
- `app/schemas/sessions.py`
  - `InterviewConfigRequest`: request body for session config creation.
  - `InterviewConfigResponse`: stored session config response.
  - `CreateSessionRequest`: request body for session creation.
  - `SessionListRequest`: query schema for paginated session listing.
  - `CreateSessionResponse`: session creation response with framework payload.
  - `SessionSummary`: lightweight session item for history list views.
  - `SessionDetailResponse`: session detail view with config and framework expansion.
  - `SessionListResponse`: paginated wrapper for session history.
  - `EndSessionResponse`: typed response for ending a session.
- `app/schemas/reports.py`
  - `RoundReview`: report-level aggregation of question, answer, and assessment.
  - `InterviewReportPayload`: structured final report body.
  - `TriggerReportResponse`: response returned when report generation is requested.
  - `TriggerReportRequest`: request body that supports `force_regenerate`.
  - `InterviewReportResponse`: stored report response with timestamps and payload.
  - `ReportStatusResponse`: compact report availability/status response used by the service layer.
- `app/schemas/__init__.py`
  - Re-exports the phase 2 schema surface for routes, tests, and later agents.

## Route Layer

- `app/api/routes/health.py`
  - `/health` is a typed health probe that returns app status and version from settings.
- `app/api/routes/assets.py`
  - `POST /api/v1/assets/resume`: accepts multipart upload, delegates to `AssetsService`, stores only mock file metadata and a mock `mock://minio/...` file ref.
  - `POST /api/v1/assets/jd`: same mock storage flow as resume upload, but appends JD metadata.
  - `POST /api/v1/assets/{asset_bundle_id}/parse`: does not call an LLM yet; it writes a deterministic mock parse payload into `parse_results` and flips the asset to `analysis_ready`.
  - `GET /api/v1/assets/{asset_bundle_id}/parse`: reads the stored parse payload and returns it through the typed response schema.
- `app/api/routes/sessions.py`
  - `POST /api/v1/sessions`: checks that the asset is parsed, fabricates a deterministic framework from the stored parse payload, writes `interview_sessions`, `interview_configs`, and `direction_frameworks`, then returns the typed framework response.
  - `GET /api/v1/sessions/{session_id}`: loads one owned session plus config/framework and serializes them into `SessionDetailResponse`.
  - `GET /api/v1/sessions`: paginates owned sessions with optional status filtering.
  - `POST /api/v1/sessions/{session_id}/end`: sets the session status to `ended` and stamps `ended_at`.
  - `POST /api/v1/sessions/{session_id}/report`: does not run async work yet; it writes a deterministic mock report payload and marks the session/report as ready immediately.
  - `GET /api/v1/sessions/{session_id}/report`: returns the stored report payload if it exists.

## WebSocket Layer

### Frame Dispatch

- Endpoint: `app/ws/endpoint.py` exposes `/ws/sessions/{session_id}`.
- Auth placeholder: websocket uses the `token` query param and the same fixed mock user as REST.
- Ownership check: the endpoint verifies that `session_id` belongs to the mock user before accepting the socket.
- Binary frame handling:
  - Any binary frame is treated as reserved for future `client.audio.chunk`.
  - Current behavior is to reply with `server.error` and `code = "not_implemented"`.
- Text frame handling:
  - Text is parsed as JSON.
  - Missing/invalid JSON or missing `event` closes the socket with unsupported-data semantics.
  - Known client text events are validated by a discriminated union.
  - Valid but unimplemented events return `server.error`.
  - Unknown event names return `server.error` with `code = "invalid_event"`.

### Event Definitions

- Client side text events:
  - `client.turn.end`
  - `client.session.pause`
  - `client.session.resume`
  - `client.session.end`
- Client side binary-reserved event:
  - `client.audio.chunk`
- Server side events defined in the contract:
  - `server.transcript.partial`
  - `server.transcript.finalized`
  - `server.turn.assessed`
  - `server.turn.compressed`
  - `server.question.generated`
  - `server.reference.ready`
  - `server.session.ended`
  - `server.error`
- `app/ws/manager.py`
  - Keeps a per-session websocket connection registry and provides `send_error`.

## Tests

- `tests/test_health.py`
  - Verifies `/health` returns `200` and the expected `status/version` payload.
- `tests/test_assets_api.py`
  - Runs the phase 2 happy path contract test: upload resume, upload JD, trigger parse, fetch parse result, and create a session.
  - Uses monkeypatching to keep the route contract stable even if service internals change.
- `tests/test_ws.py`
  - Verifies a valid client text event returns `server.error/not_implemented`.
  - Verifies a binary websocket frame also returns `server.error/not_implemented`.

## Key Phase 2 Behaviors

- REST and websocket queries are filtered by the fixed mock user from `app/api/dependencies/auth.py`.
- Uploaded files are not actually persisted yet; the asset service only stores deterministic mock storage keys.
- Parse, framework, and report outputs are mock-but-typed payloads written into PostgreSQL so the schema and route contracts can be exercised end to end.
- The websocket layer defines the final event surface early, even though all business events still return `not_implemented`.
