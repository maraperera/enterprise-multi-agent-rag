import asyncio
import json
import logging
import uuid
from contextlib import asynccontextmanager
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse
from app.config import get_settings
from app.factory import graph_lifespan
from app.graph import initial_state
from app.models import ResearchRequest, ResearchResponse
from app.security import current_user

logger = logging.getLogger("enterprise_rag")
logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    if settings.app_mode == "azure" and settings.auth_mode != "entra":
        raise RuntimeError("Azure mode requires Entra authentication")
    async with graph_lifespan() as graph:
        app.state.graph = graph
        yield


app = FastAPI(title="Enterprise Multi-Agent RAG", version="1.0.0", lifespan=lifespan)


@app.get("/health/live")
async def live():
    return {"status": "alive"}


@app.get("/health/ready")
async def ready(request: Request):
    if not getattr(request.app.state, "graph", None):
        raise HTTPException(503, "Graph not initialized")
    return {"status": "ready"}  # Local readiness only, not a downstream dependency probe.


@app.post("/v1/research", response_model=ResearchResponse)
async def research(body: ResearchRequest, request: Request, user: dict = Depends(current_user)):
    run_id = str(uuid.uuid4())
    try:
        result = await asyncio.wait_for(request.app.state.graph.ainvoke(initial_state(body.question, user["user_id"]), config={"run_name": "research", "tags": ["rag", "multi-agent"], "recursion_limit": 20}), timeout=120)
    except Exception as exc:
        logger.exception("research_failed run_id=%s error_type=%s", run_id, type(exc).__name__)
        raise HTTPException(503, "Research unavailable") from exc
    return ResearchResponse(run_id=run_id, answer=result["final_answer"], verified=result["grounded"], sources=[{k: d[k] for k in ("id", "title", "source")} for d in result["documents"]] if result["grounded"] else [])


def sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


@app.post("/v1/research/stream")
async def research_stream(body: ResearchRequest, request: Request, user: dict = Depends(current_user)):
    run_id = str(uuid.uuid4())

    async def events():
        final = None
        verified = False
        yield sse("started", {"run_id": run_id})
        try:
            async with asyncio.timeout(120):
                async for mode, payload in request.app.state.graph.astream(initial_state(body.question, user["user_id"]), stream_mode=["custom", "updates"], config={"run_name": "research_stream", "tags": ["rag", "sse"], "recursion_limit": 20}):
                    if await request.is_disconnected():
                        return
                    if mode == "custom" and isinstance(payload, dict) and payload.get("type") == "progress":
                        yield sse("progress", {"stage": payload.get("stage"), "message": payload.get("message")})
                    elif mode == "updates":
                        for node, update in payload.items():
                            if isinstance(update, dict):
                                if node == "verify":
                                    verified = bool(update.get("grounded", False))
                                if node in {"publish", "fallback", "no_evidence"}:
                                    final = update.get("final_answer")
            if final is not None:
                for start in range(0, len(final), 256):
                    yield sse("answer", {"text": final[start:start+256]})
                yield sse("completed", {"run_id": run_id, "verified": verified})
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.exception("stream_failed run_id=%s error_type=%s", run_id, type(exc).__name__)
            yield sse("error", {"run_id": run_id, "message": "Research unavailable"})

    return StreamingResponse(events(), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no", "X-Content-Type-Options": "nosniff"})
