"""Tiny offline smoke benchmark. Not a substitute for a human-labelled enterprise dataset."""
import asyncio
from app.retrieval import DemoRetriever

CASES = [
    ("What is the MFA policy?", {"it-1"}),
    ("What is the remote work policy?", {"hr-1"}),
    ("What is our AI governance policy?", {"ai-1"}),
]

async def main():
    retriever = DemoRetriever()
    recalls = []
    for question, relevant in CASES:
        results = await retriever.search(question, "demo-user", top_k=5)
        ids = {d["id"] for d in results}
        recall = len(ids & relevant) / len(relevant)
        recalls.append(recall)
        print(f"{question}: recall@5={recall:.2f}")
    score = sum(recalls) / len(recalls)
    print(f"Mean recall@5: {score:.2f}")
    if score < 1.0:
        raise SystemExit("Demo retrieval benchmark failed")

if __name__ == "__main__":
    asyncio.run(main())
