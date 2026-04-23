# Eatit Phase 3 / 3.5 Fix Plan

Source of truth for what's left. Ralph picks the first unchecked item
in "High Priority" each loop. Phase 3 detail lives in
`.ralph/specs/phase3-sections.md`; Phase 3.5 detail lives in
`.ralph/specs/phase3.5-sections.md` — pick the file matching the
section prefix.

## High Priority (work top-down)

- [ ] P3.5B.1 ObserverAgent — live coaching agent (≤ 60 char observations) — see phase3.5-sections#P3.5B.1
- [ ] P3.5B.2 Orchestrator + WS observer wiring — server.coach.observation event — see phase3.5-sections#P3.5B.2
- [ ] P3.5A.3 MetaReport frontend — list + detail page + history CTA — see phase3.5-sections#P3.5A.3
- [ ] P3.5B.3 Interview observer sidebar — panel + settings toggle — see phase3.5-sections#P3.5B.3
- [ ] P3.5X Test sweep + E2E — meta + observer smoke — see phase3.5-sections#P3.5.X

## Completed

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
