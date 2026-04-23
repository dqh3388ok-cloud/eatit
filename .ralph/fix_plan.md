# Eatit Phase 3 / 3.5 / 4 / 5 Fix Plan

Source of truth for what's left. Ralph picks the first unchecked item
in "High Priority" each loop. Section specs live in:
- `.ralph/specs/phase3-sections.md`
- `.ralph/specs/phase3.5-sections.md`
- `.ralph/specs/phase4-sections.md`
- `.ralph/specs/phase5-sections.md`

Match the section prefix to the file.

## High Priority (work top-down)

- [ ] P4.1 ASR infra — Azure Speech SDK + abstraction + mock backend — see phase4-sections#P4.1
- [ ] P4.2 WS audio protocol — binary frames + transcript events — see phase4-sections#P4.2
- [ ] P4.3 Runtime audio pipeline — streaming audio → ASR → turn answer — see phase4-sections#P4.3
- [ ] P4.4 Desktop mic permission + capture — MediaRecorder + Info.plist — see phase4-sections#P4.4
- [ ] P4.5 InterviewPage voice UX — hold-to-talk + live caption — see phase4-sections#P4.5
- [ ] P4.6 Settings voice toggle + /api/v1/asr/health — see phase4-sections#P4.6
- [ ] P4.X Phase 4 test sweep + E2E — see phase4-sections#P4.X
- [ ] P5.1 Real app icon (conditional; skip if no source PNG) — see phase5-sections#P5.1
- [ ] P5.2 Unsigned DMG build config + script — see phase5-sections#P5.2
- [ ] P5.4 Print-to-PDF on report page — see phase5-sections#P5.4
- [ ] P5.5 Sentry scaffold with secret redaction — see phase5-sections#P5.5
- [ ] P5.6 Error boundaries + WS reconnect + friendly toasts — see phase5-sections#P5.6
- [ ] P5.X Phase 5 test sweep + tauri build dry run — see phase5-sections#P5.X

## Completed

- [x] P3.5X Test sweep + E2E — meta + observer smoke (a6782c8, 2026-04-24)
- [x] P3.5B.3 Interview observer sidebar — panel + settings toggle (5bd383b, 2026-04-24)
- [x] P3.5A.3 MetaReport frontend — list + detail page + history CTA (70061b5, 2026-04-24)
- [x] P3.5B.2 Orchestrator + WS observer wiring — server.coach.observation event (adc6da3, 2026-04-24)
- [x] P3.5B.1 ObserverAgent — live coaching agent (≤ 60 char observations) (f81d72b, 2026-04-24)
- [x] P3.5A.2 MetaReport REST + storage — async pipeline + polling API (42615fa, 2026-04-24)
- [x] P3.5A.1 MetaReportAgent — cross-session trend agent (10cf62a, 2026-04-24)
- [x] P3.12 Test sweep + end-to-end smoke (85e0ff7, 2026-04-23)
- [x] P3.10c InterviewPage + HistoryPage + ReportPage — XState + WS + report fields (a090aa7, 2026-04-23)
- [x] P3.10b UploadPage + ConfigPage — real business bodies (fb0eff8, 2026-04-23)
- [x] P3.5 REST/WS real — agents wired + WS first-frame protocol (de997ea, 2026-04-23)
- [x] P3.4 LangGraph orchestrator — turn_graph + SessionRuntime TaskGroup cleanup (7307059, 2026-04-23)
- [x] P3.3 Six Agents — instructor-driven Parse / Framework / Interviewer / Reference / Compression / Report (cf96d48, 2026-04-23)
- [x] P3.8 OnboardingPage — 4-step first-run wizard + app_settings REST (50a1653, 2026-04-23)
- [x] P3.9 SettingsPage — BYOK form + test connection (5c73c88, 2026-04-23)
- [x] P3.1 LLM infra — BYOK gateway + test endpoint + header middleware (8082684, 2026-04-23)
- [x] P3.2 Prompts — six agent Jinja2 templates with guardrails (8bed096, 2026-04-23)
- [x] P3.6 app_settings table — local UI state with secret blocklist (35bea78, 2026-04-23)
- [x] P3.7 Rust keychain — macOS keyring integration + TS wrappers (19fa33a, 2026-04-23)
- [x] P3.10a AppShell + Sidebar + HomePage (83e0191, 2026-04-23)
- [x] chore: placeholder Tauri icons (d298b6d, 2026-04-23)

## Notes

- One commit per High Priority item (Conventional Commits prefix as
  specified in the section spec).
- Do not merge multiple items into one commit even if they feel related.
- Move items from "High Priority" to "Completed" in the same commit
  that implements them.
