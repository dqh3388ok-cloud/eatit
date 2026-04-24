from httpx import ASGITransport, AsyncClient

from app.main import app


async def test_asr_health_reports_available_with_whisper_installed() -> None:
    """With faster-whisper + av listed in pyproject the health probe must
    report available=true and provider=whisper. No secrets in the response."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/api/v1/asr/health")

    assert response.status_code == 200
    body = response.json()
    assert body == {"available": True, "provider": "whisper"}


async def test_asr_health_reports_unavailable_when_whisper_missing(monkeypatch) -> None:
    """If faster-whisper failed to install (e.g. platform without wheels),
    the health probe must degrade gracefully to available=false rather than
    crash the endpoint."""
    import builtins

    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name.startswith("faster_whisper"):
            raise ImportError("simulated: faster-whisper not available")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/api/v1/asr/health")

    assert response.status_code == 200
    assert response.json() == {"available": False, "provider": "whisper"}
