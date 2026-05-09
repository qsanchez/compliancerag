import structlog
from fastapi import APIRouter, HTTPException
from langsmith import traceable

from agent.graph import graph
from agent.sanitizer import sanitize
from agent.state import AgentState
from api.models import ChatRequest, ChatResponse

logger = structlog.get_logger()

router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
@traceable(name="chat", run_type="chain")
def chat(request: ChatRequest) -> ChatResponse:
    try:
        question = sanitize(request.question)
    except ValueError:
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

    logger.info(
        "chat_request",
        question=request.question,
        route=result.get("route"),
        citations=result.get("citations"),
    )

    return ChatResponse(
        answer=result["answer"],
        citations=result["citations"],
        route=result.get("route"),
        chart_b64=result.get("chart_b64"),
    )
