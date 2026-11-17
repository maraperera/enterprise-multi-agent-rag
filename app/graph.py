from typing import TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.config import get_stream_writer


class ResearchState(TypedDict):
    question: str
    user_id: str
    documents: list[dict]
    benefits: str
    risks: str
    draft: str
    grounded: bool
    verification_reason: str
    final_answer: str


def initial_state(question: str, user_id: str) -> ResearchState:
    return {"question": question, "user_id": user_id, "documents": [], "benefits": "", "risks": "", "draft": "", "grounded": False, "verification_reason": "", "final_answer": ""}


def build_graph(retriever, agents):
    def progress(stage, message):
        get_stream_writer()({"type": "progress", "stage": stage, "message": message})

    async def retrieve(state: ResearchState):
        progress("retrieval", "Searching authorized documents")
        documents = await retriever.search(state["question"], state["user_id"])
        progress("retrieval", f"Retrieved {len(documents)} passages")
        return {"documents": documents}

    def branch(state):
        return ["benefits", "risks"] if state["documents"] else ["no_evidence"]

    async def benefits(state):
        result = await agents.benefits(state["question"], state["documents"])
        progress("benefits", "Completed")
        return {"benefits": result}

    async def risks(state):
        result = await agents.risks(state["question"], state["documents"])
        progress("risks", "Completed")
        return {"risks": result}

    async def write(state):
        draft = await agents.write(state["question"], state["documents"], state["benefits"], state["risks"])
        progress("writer", "Draft completed")
        return {"draft": draft}

    async def verify(state):
        verdict = await agents.verify(state["draft"], state["documents"])
        # Enforce that citations, if present, reference existing evidence.
        import re
        citations = [int(x) for x in re.findall(r"\[(\d+)\]", state["draft"])]
        citations_valid = all(1 <= x <= len(state["documents"]) for x in citations)
        grounded = bool(verdict.grounded and citations_valid)
        progress("verification", "Passed" if grounded else "Failed")
        return {"grounded": grounded, "verification_reason": verdict.reason}

    def publication(state):
        return "publish" if state["grounded"] else "fallback"

    def publish(state):
        return {"final_answer": state["draft"]}

    def fallback(state):
        return {"final_answer": "The draft could not be sufficiently verified against authorized evidence."}

    def no_evidence(state):
        return {"final_answer": "No authorized supporting documents were found."}

    builder = StateGraph(ResearchState)
    for name, node in [("retrieve", retrieve), ("benefits", benefits), ("risks", risks), ("write", write), ("verify", verify), ("publish", publish), ("fallback", fallback), ("no_evidence", no_evidence)]:
        builder.add_node(name, node)
    builder.add_edge(START, "retrieve")
    builder.add_conditional_edges("retrieve", branch)
    builder.add_edge(["benefits", "risks"], "write")
    builder.add_edge("write", "verify")
    builder.add_conditional_edges("verify", publication)
    for name in ("publish", "fallback", "no_evidence"):
        builder.add_edge(name, END)
    return builder.compile()
