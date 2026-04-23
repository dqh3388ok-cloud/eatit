"""Structured logging configuration.

Leak-prevention doc comment (Phase 3/4 constraint A1 + C):
- Never log full HTTP headers (they may contain `X-LLM-Config`). Log only
  method / path / status / duration at the request boundary.
- Never bind raw LLM or ASR secret values to structlog contextvars.
  `SecretStr.__repr__` masks but only if the value is wrapped — raw strings
  still leak.
- If you need to log an LLM or ASR config at all, log its `repr()` (which
  masks the secret) or pick individual non-secret fields by name.
"""

import logging
import sys

import structlog


def configure_logging() -> None:
    processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ]

    structlog.configure(
        processors=processors,
        logger_factory=structlog.PrintLoggerFactory(file=sys.stdout),
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    return structlog.get_logger(name)
