import time

import structlog
from fastapi import APIRouter, HTTPException
from langsmith import traceable

from agent.graph import graph
from agent.sanitizer import sanitize
from agent.state import AgentState
from api.models import ChatRequest, ChatResponse
from audit.logger import AuditRecord, log_query
from config import get_settings

logger = structlog.get_logger()

router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
@traceable(name="chat", run_type="chain")
def chat(request: ChatRequest) -> ChatResponse:
    t0 = time.perf_counter()

    try:
        question = sanitize(request.question)
        injection_blocked = False
    except ValueError:
        log_query(AuditRecord(
            question=request.question[:500],
            injection_blocked=True,
            model_version=get_settings().bedrock_model_id,
        ))
        raise HTTPException(status_code=400, detail="Invalid input.")

    initial: AgentState = {
        "question": question,
        "history": request.history,
        "route": None,
        "analytics_result": None,
        "chart_b64": None,
        "answer": "",
        "citations": [],
    }

    result = graph.invoke(initial)

    if not result.get("answer"):
        raise HTTPException(
            status_code=404,
            detail="No relevant information found for this question.",
        )

    latency_ms = (time.perf_counter() - t0) * 1000

    logger.info(
        "chat_request",
        question=question,
        route=result.get("route"),
        citations=result.get("citations"),
        latency_ms=round(latency_ms, 1),
    )

    log_query(AuditRecord(
        question=question,
        route=result.get("route"),
        answer=result.get("answer"),
        citations=result.get("citations", []),
        has_chart=result.get("chart_b64") is not None,
        model_version=get_settings().bedrock_model_id,
        latency_ms=round(latency_ms, 1),
        injection_blocked=injection_blocked,
    ))

    return ChatResponse(
        answer=result["answer"],
        citations=result["citations"],
        route=result.get("route"),
        chart_b64=result.get("chart_b64"),
    )
