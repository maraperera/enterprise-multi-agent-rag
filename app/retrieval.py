"""Retrieval adapters. The Azure index must have filterable owner_id and vector field content_vector."""
from azure.search.documents.models import VectorizedQuery

DEMO_DOCS = [
    {"id": "it-1", "title": "MFA policy", "source": "it-security", "content": "All employees must use multifactor authentication for corporate systems.", "owner_id": "demo-user"},
    {"id": "hr-1", "title": "Remote work", "source": "hr-handbook", "content": "Employees may request remote work subject to approval and role requirements.", "owner_id": "demo-user"},
    {"id": "ai-1", "title": "AI governance", "source": "ai-governance", "content": "AI deployments require human oversight, access control, evaluation, and incident logging.", "owner_id": "demo-user"},
]


class DemoRetriever:
    async def search(self, question: str, user_id: str, top_k: int = 5) -> list[dict]:
        terms = set(question.lower().split())
        scored = []
        for doc in DEMO_DOCS:
            if doc["owner_id"] != user_id:
                continue
            words = set((doc["title"] + " " + doc["content"]).lower().split())
            score = len(terms & words)
            if score:
                scored.append((score, doc))
        scored.sort(key=lambda x: -x[0])
        return [{k: v for k, v in doc.items() if k != "owner_id"} for _, doc in scored[:top_k]]


class AzureRetriever:
    def __init__(self, search_client, embeddings, semantic_config: str):
        self.client = search_client
        self.embeddings = embeddings
        self.semantic_config = semantic_config

    async def search(self, question: str, user_id: str, top_k: int = 5) -> list[dict]:
        vector = await self.embeddings.aembed_query(question)
        escaped = user_id.replace("'", "''")
        results = await self.client.search(
            search_text=question,
            vector_queries=[VectorizedQuery(vector=vector, k_nearest_neighbors=50, fields="content_vector")],
            filter=f"owner_id eq '{escaped}'",
            query_type="semantic",
            semantic_configuration_name=self.semantic_config,
            select=["id", "title", "source", "content"],
            top=top_k,
        )
        return [{key: item[key] for key in ("id", "title", "source", "content")} async for item in results]
