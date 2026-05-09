from typing import Literal, TypedDict


class AgentState(TypedDict):
    question: str
    history: list[dict]  # [{"role": "user"|"assistant", "content": str}]
    route: Literal["rag", "analytics"] | None
    analytics_result: dict | None  # kept for Block 2 chart generation
    chart_b64: str | None
    answer: str
    citations: list[str]
