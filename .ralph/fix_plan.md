# Eatit Phase 3 Fix Plan

Source of truth for what's left in Phase 3. Ralph picks the first
unchecked item in "High Priority" each loop. Details for each item
live in `.ralph/specs/phase3-sections.md` under the matching anchor.

## High Priority (work top-down)

- [ ] P3.3 Six Agents — Parse / Framework / Interviewer / Reference / Compression / Report with Instructor — see specs#P3.3
- [ ] P3.4 LangGraph orchestrator — turn_graph + TaskGroup + on_session_end — see specs#P3.4
- [ ] P3.5 REST/WS real — replace Phase 2 mocks + client.session.init first-frame — see specs#P3.5
- [ ] P3.10b UploadPage + ConfigPage — real business bodies — see specs#P3.10b
- [ ] P3.10c InterviewPage + HistoryPage + ReportPage — XState + WS + report fields — see specs#P3.10c
- [ ] P3.12 Test sweep + end-to-end smoke — see specs#P3.12

## Completed

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
