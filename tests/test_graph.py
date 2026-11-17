import pytest
from app.graph import build_graph, initial_state
from app.agents import DemoAgents
from app.models import Verdict


class EmptyRetriever:
    async def search(self, question, user_id, top_k=5):
        return []


class FixedRetriever:
    async def search(self, question, user_id, top_k=5):
        return [{"id": "1", "title": "Policy", "source": "policy", "content": "MFA is required"}]


class RejectingAgents(DemoAgents):
    async def verify(self, draft, documents):
        return Verdict(grounded=False, reason="Unsupported")


@pytest.mark.asyncio
async def test_no_evidence_short_circuits():
    graph = build_graph(EmptyRetriever(), DemoAgents())
    result = await graph.ainvoke(initial_state("What is the policy?", "user"))
    assert not result["grounded"]
    assert result["final_answer"] == "No authorized supporting documents were found."


@pytest.mark.asyncio
async def test_verifier_blocks_draft():
    graph = build_graph(FixedRetriever(), RejectingAgents())
    result = await graph.ainvoke(initial_state("What is the MFA policy?", "user"))
    assert result["final_answer"] != result["draft"]
    assert result["grounded"] is False


@pytest.mark.asyncio
async def test_parallel_agents_contribute():
    graph = build_graph(FixedRetriever(), DemoAgents())
    result = await graph.ainvoke(initial_state("What is the MFA policy?", "user"))
    assert result["benefits"] and result["risks"]
    assert result["grounded"] is True
