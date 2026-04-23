from __future__ import annotations

import sentry_sdk

from app.infra.observability.sentry import before_send, init_sentry


def test_init_sentry_is_noop_when_dsn_empty() -> None:
    initialized = init_sentry(dsn="", environment="test")

    assert initialized is False
    # No network traffic should have been configured. We don't assert the
    # Hub state because other tests may have initialized it; the contract
    # here is the False return + never calling sentry_sdk.init internally.
    _ = sentry_sdk  # silence unused-import flag when the assertion above is enough


def test_before_send_redacts_x_llm_config_header() -> None:
    event = {
        "request": {
            "headers": {
                "X-LLM-Config": "base64-secret-header-do-not-leak",
                "Content-Type": "application/json",
            }
        }
    }

    scrubbed = before_send(event)

    assert scrubbed["request"]["headers"]["X-LLM-Config"] == "<redacted>"
    # Non-secret headers pass through intact.
    assert scrubbed["request"]["headers"]["Content-Type"] == "application/json"


def test_before_send_redacts_azure_speech_env_vars() -> None:
    event = {
        "contexts": {
            "runtime": {
                "env": {
                    "AZURE_SPEECH_KEY": "subscription-should-never-surface",
                    "AZURE_SPEECH_REGION": "eastasia",
                    "APP_ENV": "development",
                }
            }
        }
    }

    scrubbed = before_send(event)

    env = scrubbed["contexts"]["runtime"]["env"]
    assert env["AZURE_SPEECH_KEY"] == "<redacted>"
    assert env["AZURE_SPEECH_REGION"] == "<redacted>"
    # Non-secret env still readable.
    assert env["APP_ENV"] == "development"


def test_before_send_redacts_interview_turn_answer_text() -> None:
    event = {
        "extra": {
            "turn_index": 2,
            "answer": "候选人原话,可能含 PII",
            "question": "你怎么衡量这个指标?",
        }
    }

    scrubbed = before_send(event)

    assert scrubbed["extra"]["answer"] == "<redacted>"
    # Non-PII fields are preserved so debugging stays useful.
    assert scrubbed["extra"]["turn_index"] == 2
    assert scrubbed["extra"]["question"] == "你怎么衡量这个指标?"
