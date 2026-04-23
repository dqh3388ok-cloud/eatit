"""Sentry scaffold with secret-redacting `before_send`.

Behavior:
- `init_sentry(dsn, environment)` is a no-op when `dsn` is empty. Production
  deployments set `SENTRY_DSN` in `.env`; dev env leaves it blank so no
  outbound traffic is ever emitted by default.
- `before_send(event, hint)` walks the event structure and masks anything
  that smells like an LLM key, an ASR key, or the candidate's free-text
  answer. This is a hard invariant — see phase3-constraints §C and P5.5.

Redacted targets (key match, case-insensitive, keys normalized via `lower()`):
- `x-llm-config` (header carrying base64 LLMConfig on every request)
- any key containing `api_key` / `subscription` / `llm_config` / `azure_speech`
- `authorization`, `bearer`, `token`, `password`           (generic auth)
- `answer`                                                  (InterviewTurn PII)

Value targets:
- `bytes` values are replaced with `"<bytes len=N>"` so raw opus audio
  chunks never reach Sentry intact.
"""

from __future__ import annotations

from typing import Any

import sentry_sdk


_REDACTED = "<redacted>"

_SECRET_EXACT_KEYS: frozenset[str] = frozenset(
    {
        "authorization",
        "bearer",
        "token",
        "password",
        "apikey",
        "answer",
    }
)

# Substring probes kept generic enough not to reference the literal env
# name or the Azure SDK's field name — those live only in
# app/infra/asr/{config,factory,azure_backend}.py, enforced by the
# meta-test at tests/infra/test_asr.py::test_no_secret_token_leakage_in_app_tree.
_SECRET_KEY_SUBSTRINGS: tuple[str, ...] = (
    "llm-config",
    "llm_config",
    "azure_speech",
    "api_key",
    "subscription",
)


def _is_secret_key(key: object) -> bool:
    if not isinstance(key, str):
        return False
    normalized = key.lower()
    if normalized in _SECRET_EXACT_KEYS:
        return True
    for probe in _SECRET_KEY_SUBSTRINGS:
        if probe in normalized:
            return True
    return False


def _redact_node(node: Any) -> Any:
    if isinstance(node, dict):
        return {
            key: (
                _REDACTED
                if _is_secret_key(key)
                else _redact_node(value)
            )
            for key, value in node.items()
        }
    if isinstance(node, list):
        return [_redact_node(item) for item in node]
    if isinstance(node, tuple):
        return tuple(_redact_node(item) for item in node)
    if isinstance(node, (bytes, bytearray, memoryview)):
        length = len(bytes(node))
        return f"<bytes len={length}>"
    return node


def before_send(event: dict[str, Any], hint: dict[str, Any] | None = None) -> dict[str, Any]:
    """Sentry `before_send` hook. Returns the scrubbed event; never drops it."""
    _ = hint  # reserved for future use (e.g. attaching span context safely)
    return _redact_node(event)


def init_sentry(dsn: str, environment: str) -> bool:
    """Initialize Sentry if a non-empty DSN is provided.

    Returns True when the SDK was initialized, False when skipped. Tests
    rely on the False return to assert zero overhead in dev.
    """
    if not dsn:
        return False

    sentry_sdk.init(
        dsn=dsn,
        environment=environment,
        traces_sample_rate=0.1,
        send_default_pii=False,
        before_send=before_send,
    )
    return True
