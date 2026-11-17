import pytest
from httpx import ASGITransport, AsyncClient
from app.main import app
from app.factory import graph_lifespan


@pytest.mark.asyncio
async def test_health():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/health/live")
        assert response.status_code == 200


@pytest.mark.asyncio
async def test_research_and_no_evidence():
    async with graph_lifespan() as graph:
        app.state.graph = graph
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post("/v1/research", json={"question": "What is the MFA policy?"})
            assert response.status_code == 200
            data = response.json()
            assert data["verified"] is True
            assert data["sources"]
            no_evidence = await client.post("/v1/research", json={"question": "zzzxxyy unfindable"})
            assert no_evidence.status_code == 200
            assert no_evidence.json()["verified"] is False
            assert no_evidence.json()["sources"] == []


@pytest.mark.asyncio
async def test_sse_does_not_leak_draft_updates():
    async with graph_lifespan() as graph:
        app.state.graph = graph
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post("/v1/research/stream", json={"question": "What is the MFA policy?"})
            assert response.status_code == 200
            assert "event: progress" in response.text
            assert "event: completed" in response.text
            assert "event: answer" in response.text
            assert '"draft"' not in response.text


@pytest.mark.asyncio
async def test_invalid_question():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/v1/research", json={"question": "a"})
        assert response.status_code == 422
