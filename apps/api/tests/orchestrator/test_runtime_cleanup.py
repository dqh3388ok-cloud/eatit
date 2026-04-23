from __future__ import annotations

import gc
import weakref

import pytest
from pydantic import SecretStr

from app.infra.llm.config import LLMConfig
from app.orchestrator.runtime import SessionClosedError, SessionRuntime


@pytest.fixture
def config() -> LLMConfig:
    return LLMConfig(
        provider="openai",
        api_key=SecretStr("sk-weakref-test-only"),
        model="gpt-4o-mini",
        base_url=None,
    )


async def test_on_session_end_releases_llm_config() -> None:
    # Built inline rather than via fixture so pytest isn't holding an
    # additional strong reference while the weakref test runs.
    runtime = SessionRuntime(
        session_id="session-weakref",
        llm_config=LLMConfig(
            provider="openai",
            api_key=SecretStr("sk-weakref-test-only"),
            model="gpt-4o-mini",
            base_url=None,
        ),
    )
    ref = weakref.ref(runtime._llm_config)
    assert ref() is not None

    await runtime.on_session_end()
    gc.collect()

    assert ref() is None, "LLMConfig still reachable after on_session_end + gc.collect()"
    assert runtime._gateway is None
    assert runtime._llm_config is None


async def test_on_session_end_is_idempotent(config: LLMConfig) -> None:
    runtime = SessionRuntime(session_id="session-idempotent", llm_config=config)
    await runtime.on_session_end()
    # Second call must not raise even though state is already torn down.
    await runtime.on_session_end()


async def test_run_turn_after_close_raises(config: LLMConfig) -> None:
    runtime = SessionRuntime(session_id="session-closed", llm_config=config)
    await runtime.on_session_end()

    with pytest.raises(SessionClosedError):
        await runtime.run_turn(
            turn_index=1,
            question="Q",
            answer="A",
            framework_json="{}",
        )
