from httpx import ASGITransport, AsyncClient

from app.infra.config import get_settings
from app.main import app


async def test_asr_health_reports_unavailable_when_env_missing(monkeypatch) -> None:
    """Default dev env has no AZURE_SPEECH_KEY / AZURE_SPEECH_REGION, so the
    probe must report available=false without leaking any secret material."""
    get_settings.cache_clear()
    monkeypatch.setenv("AZURE_SPEECH_KEY", "")
    monkeypatch.setenv("AZURE_SPEECH_REGION", "")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/api/v1/asr/health")

    assert response.status_code == 200
    assert response.json() == {"available": False, "provider": "azure"}
    get_settings.cache_clear()


async def test_asr_health_reports_available_when_env_present(monkeypatch) -> None:
    get_settings.cache_clear()
    monkeypatch.setenv("AZURE_SPEECH_KEY", "mock-subscription")
    monkeypatch.setenv("AZURE_SPEECH_REGION", "eastasia")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/api/v1/asr/health")

    assert response.status_code == 200
    body = response.json()
    assert body == {"available": True, "provider": "azure"}
    # Defensive: the subscription key must never surface in the response.
    assert "mock-subscription" not in response.text
    get_settings.cache_clear()
