from __future__ import annotations

import anyio
from httpx import ASGITransport, AsyncClient

from app.main import app


async def test_trigger_report_completes_via_asyncio_task_queue() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        resume_response = await client.post(
            "/api/v1/assets/resume",
            files={"file": ("resume.txt", b"resume-content", "text/plain")},
        )
        asset_id = resume_response.json()["asset_bundle_id"]

        await client.post(
            "/api/v1/assets/jd",
            files={"file": ("jd.txt", b"jd-content", "text/plain")},
            data={"asset_bundle_id": asset_id},
        )
        await client.post(f"/api/v1/assets/{asset_id}/parse")
        session_response = await client.post(
            "/api/v1/sessions",
            json={
                "asset_bundle_id": asset_id,
                "config": {
                    "style": "standard_professional",
                    "direction": "project_deep_dive",
                    "duration_minutes": 20,
                },
            },
        )
        session_id = session_response.json()["session_id"]

        trigger_response = await client.post(f"/api/v1/sessions/{session_id}/report", json={})

        assert trigger_response.status_code == 200
        assert trigger_response.json()["status"] == "generating"

        final_status_code = 0
        final_payload: dict[str, object] | None = None
        for _ in range(20):
            report_response = await client.get(f"/api/v1/sessions/{session_id}/report")
            final_status_code = report_response.status_code
            if report_response.status_code == 200:
                final_payload = report_response.json()
                break
            assert report_response.status_code == 409
            await anyio.sleep(0.05)

    assert final_status_code == 200
    assert final_payload is not None
    assert final_payload["status"] == "ready"
    assert len(final_payload["payload"]["round_reviews"]) == 1
