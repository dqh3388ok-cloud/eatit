"""Observability primitives: Sentry scaffold with secret-redacting before_send."""

from app.infra.observability.sentry import before_send, init_sentry

__all__ = ["before_send", "init_sentry"]
