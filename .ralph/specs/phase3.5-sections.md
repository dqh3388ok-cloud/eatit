# Phase 3.5 Sections — MetaReport + Observer Sidebar

Phase 3.5 finishes the non-voice non-packaging work that Phase 3
deferred (handoff doc line 193). Two product features, independent
delivery, both reuse the agent infrastructure + BYOK header protocol
already in place. Phase 3 hard constraints
(`phase3-constraints.md`) all still apply — no relaxations.

## Feature 3.5A — MetaReport (cross-session trend analysis)

**Why.** A single InterviewReport tells the user how one session went.
After 3–10 sessions, the more useful question is "what am I
consistently weak on, and am I getting better?" — which no per-session
report answers. MetaReport takes N reports, finds recurring weakness
patterns, improvement signals, and a pass-probability trajectory.

**User surface.** Under sidebar "我的数据" we add a third item "综合分析"
(after 面试记录 / 评估报告). The 面试记录 page gets a CTA
"生成综合分析 (N 场)" enabled when user has ≥ 2 reports.

### P3.5A.1 — MetaReportAgent

**Files (apps/api/):**
- `app/prompts/meta_report/{system,user}.j2`
- `app/agents/meta_report/{__init__,schemas,service}.py`
- `app/prompts/__init__.py` — add `meta_report` to `AGENT_NAMES`
- `tests/agents/test_meta_report.py` — 3 cases (happy / malformed-then-recover / network error propagation)

**Output schema (Pydantic):**
```python
class RecurringWeakness(BaseModel):
    aspect: str
    occurrence_count: int                       # >= 2 to qualify as "recurring"
    session_ids: list[str]
    evidence_quotes: list[str]                  # from the reasons[].quote fields

class ImprovementSignal(BaseModel):
    aspect: str
    from_verdict: Literal["weak","mixed","solid","strong"]
    to_verdict: Literal["weak","mixed","solid","strong"]
    earlier_session_id: str
    later_session_id: str

class PassProbabilityPoint(BaseModel):
    session_id: str
    session_created_at: datetime
    pass_probability: int                       # 0..100

class NextFocusArea(BaseModel):
    aspect: str
    reason: str
    suggested_prep: str                         # 1 concrete sentence of action

class MetaReportOutput(BaseModel):
    overall_trend_summary: str                  # 200–400 chars
    recurring_weaknesses: list[RecurringWeakness]
    improvement_signals: list[ImprovementSignal]
    pass_probability_series: list[PassProbabilityPoint]
    next_focus_areas: list[NextFocusArea]       # 3–5
```

**Prompt design.** System tells the agent its job is trend analysis
across reports. User template bundles the N reports as JSON including
session_created_at + config_snapshot + the full payload. The agent
must ground every claim in at least one real session_id.

**N=1 degrade rule (explicit in system.j2).** When only one report is
provided, the agent MUST:
- return `recurring_weaknesses=[]` and `improvement_signals=[]` (no
  fabrication of patterns from a single data point)
- put `overall_trend_summary` in single-session retrospective voice
  ("这一场你在...") not trend voice ("你在几次面试里...")
- keep `pass_probability_series` as 1 point (still valid)
- allow `next_focus_areas` (actionable from single report's reasons)
Tests lock this in; future prompt tuning must preserve the contract.

**Acceptance.** `uv run pytest tests/agents/test_meta_report.py` — all
3 cases green. `rg -n "pass_probability_series" apps/api/app/agents/`
shows the field exists with the points list type.

**Commit.** `feat(agents): meta report agent for cross-session trends`

### P3.5A.2 — MetaReport storage + REST

**Files (apps/api/):**
- Alembic migration `20260424_0001_meta_reports.py` — table
  `meta_reports(id PK String36, user_id FK, covered_session_ids JSON,
  status String, payload JSON nullable, created_at, updated_at)`
- `app/models/meta_report.py` + re-export in `app/models/__init__.py`
- `app/domain/meta_reports/service.py` — `trigger_meta_report`,
  `get_meta_report`, `list_meta_reports`
- `app/api/routes/meta_reports.py`:
  - `POST /api/v1/meta-reports` body `{session_ids: list[str]}` — if
    empty or missing, covers all reports in DB; requires ≥ 1 session
    with a ready report; 0 reports → 400
    `{"detail": "至少需要 1 场已完成的面试"}`
  - `GET /api/v1/meta-reports/{id}` — 404 not found / 409 still
    generating / 200 ready (polling pattern, same as single report)
  - `GET /api/v1/meta-reports?page&page_size` — list
- `app/api/router.py` — register
- Heavy work runs via the existing `TaskQueue` asyncio backend so the
  POST returns 202 + a task_id; the agent runs in the background.
- `tests/api/test_meta_reports_api.py` — 6 cases:
  1. POST with 0 reports → 400
  2. POST with 1 report → 202 + id (single-session retrospective path)
  3. POST with ≥ 2 reports → 202 + id (cross-session path)
  4. GET while in-flight → 409
  5. GET after success (N=1) → 200 with payload; `recurring_weaknesses`
     and `improvement_signals` are `[]` (agent saw no cross-session
     data); `pass_probability_series` has 1 point; `overall_trend_summary`
     is phrased as single-session retrospective
  6. POST then LLMError during agent run → status=failed, GET returns
     200 with status=failed + detail in payload (no 5xx)

**Key judgment.** `covered_session_ids` is captured at trigger time
(snapshot). Subsequent new sessions don't invalidate an older
MetaReport — you simply generate a new one.

**Acceptance.** `uv run pytest tests/api/test_meta_reports_api.py` + all
prior tests green. `uv run alembic heads` shows `20260424_0001` at head.

**Commit.** `feat(api): meta report REST + storage + async pipeline`

### P3.5A.3 — MetaReport frontend

**Files (apps/desktop/src/):**
- `api/metaReports.ts` — typed client
- `pages/MetaReportPage.tsx` at route `/meta-report/:id`
  - Skeleton while `status=generating`, error card for `status=failed`
  - **Trend summary card** (serif H2, body text)
  - **Pass probability trajectory** — plain SVG `<polyline>` with
    session dots (no chart library; keeps bundle small). X-axis = session
    created_at, Y-axis = probability 0–100.
  - **Recurring weaknesses** — each row shows aspect + occurrence badge +
    evidence_quotes expandable
  - **Improvement signals** — green pill rows "X: mixed → solid
    (session A → session B)"
  - **Next focus areas** — 3–5 `.ds-card` rows with aspect + reason +
    suggested_prep
- `pages/HistoryPage.tsx` — add "生成综合分析" button at top; enabled
  when there is ≥ 1 ready report; opens modal to select session subset
  (all selected by default), POST on confirm, navigate to
  `/meta-report/{id}`. The modal must note "只选 1 场时生成单场复盘" so
  the user knows the trade-off before confirming.
- `components/Sidebar.tsx` — add "综合分析" nav item under "我的数据"
  (pointing to a list page — see next)
- `pages/MetaReportListPage.tsx` at route `/meta-reports` — list of
  past meta-reports with created_at + session_count

**Acceptance.** `pnpm exec tsc --noEmit` + `pnpm lint` clean.
`pnpm build` succeeds. `grep -n "pass_probability_series" apps/desktop/src/pages/`
hits the MetaReportPage.

**Commit.** `feat(desktop): meta report page + history trigger`

---

## Feature 3.5B — Observer Sidebar (live AI coaching)

**Why.** During the live interview the candidate currently gets no
signal until the report is generated at the end. A quiet in-turn AI
observer can flag drift ("你刚才偏离了问题,可以拉回来"), recognize a
strong moment ("这一段量化很到位,保持"), or nudge pace ("还有 5 分钟,
可以收一下"). Lightweight, between-turn only — not a real-time typing
coach (that would be distracting + expensive).

### P3.5B.1 — ObserverAgent

**Files (apps/api/):**
- `app/prompts/observer/{system,user}.j2`
- `app/agents/observer/{__init__,schemas,service}.py`
- `tests/agents/test_observer.py` — 3 cases

**Output schema:**
```python
class ObserverAgentOutput(BaseModel):
    observation: str                            # <= 60 chars, one sentence
    tone: Literal["support","alert","pivot"]
    actionable: bool                            # true iff user should change strategy
```

**Prompt constraint.** Hard 60-char cap. Agent addresses the candidate
directly with "你" (decision #5). Tone choice rules in the system
prompt:
- `support` — strong answer worth reinforcing ("你这段量化很到位")
- `alert`  — drift / unclear / content-safety smell ("你偏题了,拉回来")
- `pivot`  — time pressure / wrapping up ("还剩 5 分钟,可以收尾了")

**Acceptance.** 3 tests green. Prompt test
`tests/prompts/test_prompt_load.py` already parameterizes over
`AGENT_NAMES` — adding `observer` to `app/prompts/__init__.py` auto-
includes it.

**Commit.** `feat(agents): observer agent for live interview coaching`

### P3.5B.2 — Orchestrator + WS wiring

**Files (apps/api/):**
- `app/orchestrator/events.py` — add `ObserverObservationEvent`
- `app/orchestrator/runtime.py`:
  - Spawn an observer task inside `run_turn` alongside the
    reference-answer task — fire-and-forget, tracked in a new
    `_observer_tasks` set so `on_session_end()` cancels them
  - Each task reads the just-finished TurnState, calls ObserverAgent,
    enqueues an `ObserverObservationEvent(turn_index, observation, tone, actionable)`
  - On failure: silent (same policy as reference). Observer is
    advisory; a broken observer must never break the interview
- `app/ws/endpoint.py` — `_serialize_event` case for the new event →
  `server.coach.observation`
- `app/ws/schemas.py` — add the server event type
- `tests/orchestrator/test_observer_wiring.py` — 2 cases:
  1. Happy path: mock ObserverAgent, assert event is enqueued and
     shape matches schema
  2. Observer raises → turn still completes, event NOT enqueued, no
     exception propagates
- `tests/orchestrator/test_runtime_cleanup.py` — extend weakref
  assertion to also prove observer tasks are cancelled + joined

**Concurrency budget.** Observer must not delay the next-question
generation. Because it's spawned outside the turn_graph TaskGroup
(like the reference task) it already runs in parallel. Add a defensive
`asyncio.wait_for(..., 4.0)` in the observer task — if upstream is
slow, we swallow rather than pile up.

**Rate-limit policy.** Exactly one observer call per turn, even if
the client re-sends a turn.end (should never happen under normal
flow; guard anyway with a `_observed_turns: set[int]`).

**Acceptance.** `uv run pytest` all green including the 2 new + the
extended cleanup test. `rg -n "ObserverObservationEvent" apps/api/app/`
shows wiring in runtime + ws.

**Commit.** `feat(orchestrator): observer task + server.coach.observation`

### P3.5B.3 — Interview page sidebar

**Files (apps/desktop/src/):**
- `pages/interview/ObserverPanel.tsx` — right-rail panel (fixed width,
  scrollable); each observation is a small card with tone-colored
  dot (`support` = brand green, `alert` = warn orange, `pivot` = info
  blue), short text, timestamp
- `pages/InterviewPage.tsx` — wrap main + panel in a 2-col grid when
  observer enabled; route new `server.coach.observation` events into
  an `observations: ObserverEntry[]` XState context field
- `statecharts/interview-machine.ts` — new action `appendObservation`
- `api/appSettings.ts` — new whitelisted key `observer_panel_enabled`
  (boolean, default true)
- `pages/SettingsPage.tsx` — add toggle "AI 观察侧栏" in a new
  "面试体验" section
- `app/domain/settings/service.py` — extend `ALLOWED_KEYS` with
  `observer_panel_enabled`
- `tests/domain/test_app_settings.py` — parametrize the allow-list
  test over the new key too

**Accessibility.** Panel collapses to a narrow strip with a chevron
when disabled or when viewport < 1100px.

**Acceptance.** `pnpm exec tsc --noEmit` + `pnpm lint` clean.
`pnpm build` succeeds. `grep -n "server.coach.observation"
apps/desktop/src/` hits InterviewPage. Manual: after toggling off in
Settings, panel hides on next mount of `/interview/:id`.

**Commit.** `feat(desktop): observer sidebar on interview page`

---

## P3.5.X — Test sweep + E2E

Same shape as P3.12. Additional coverage:
- E2E with 3 mock sessions → POST /meta-reports → assert shape
- Single-turn WS test that includes observer event in the drain output

**Commit.** `test: phase 3.5 integration and smoke sweep`

---

## Execution order (Ralph picks top-down)

| # | Section | Deps | Est |
|---|---|---|---|
| 1 | P3.5A.1 MetaReport agent | — | 0.5d |
| 2 | P3.5A.2 MetaReport REST + DB | P3.5A.1 | 0.75d |
| 3 | P3.5B.1 Observer agent | — | 0.5d |
| 4 | P3.5B.2 Orchestrator + WS wiring | P3.5B.1 | 0.75d |
| 5 | P3.5A.3 MetaReport frontend | P3.5A.2 | 1d |
| 6 | P3.5B.3 Interview observer sidebar | P3.5B.2 | 0.5d |
| 7 | P3.5.X Test sweep + E2E | 1–6 | 0.25d |

**Baseline total: ~4.25 days** (Ralph velocity today suggests ~1–2
hours wall clock).

---

## Product decisions (locked)

| # | 决策项 | 值 |
|---|---|---|
| 1 | MetaReport 触发阈值 | **≥ 1** session(N=1 时 agent 走单场复盘降级路径,不硬吐空的 recurring/improvement 数组) |
| 2 | MetaReport 重生成策略 | 每次生成一条新记录入库,历史保留,不原地 upsert |
| 3 | Observer 默认开关 | 默认**开**;用户可在 Settings 关 |
| 4 | Observer 视觉位置 | InterviewPage **右侧侧栏** |
| 5 | Observer prompt 语气 | 对候选人用**第二人称"你"** |
| 6 | Settings toggle 放置 | Settings 页新开 "面试体验" 区 |

其余技术选择(Instructor / gateway / WS 事件形状 / SVG polyline / observer fire-and-forget)按 Phase 3 既有风格,不再罗列。

## 架构边界(保持不变)

- A1–A4 红线仍在(无 key 泄漏 / WS 首帧 / TaskGroup 清理 / Report 字段)
- 测试覆盖 ≥ 85% 新代码
- 一节一 commit,Conventional Commits prefix 按上文
- Observer 任务绑到 `on_session_end()` 的 cleanup,不得外泄 LLMConfig

## 产物

结束时代码层面:
- 2 张新表(`meta_reports`)
- 2 个新 agent(MetaReport / Observer)
- 3 个新 REST 端点组
- 1 个新 WS 事件类型
- 2 个新前端主页面(MetaReport / MetaReportList)+ 1 个观察侧栏组件
- 1 个新 app_settings 白名单 key(observer_panel_enabled)
- 约 15–20 个新测试,pytest 目标 > 110 用例

Ralph 跑完,`EXIT_SIGNAL: true` 条件照旧:fix_plan 全勾 + pytest/tsc/lint/cargo check 四套绿 + 工作树 clean。
