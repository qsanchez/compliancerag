from typing import Literal

from langgraph.graph import END, START, StateGraph

from agent.router import classify
from agent.state import AgentState
from agent.tools.generate_chart import generate_chart
from agent.tools.query_metrics import query_metrics
from agent.tools.search_regulations import search_regulations


def _router_node(state: AgentState) -> dict:
    return {"route": classify(state["question"])}


def _rag_node(state: AgentState) -> dict:
    result = search_regulations(state["question"], state.get("history"))
    return {"answer": result["answer"], "citations": result["citations"]}


def _analytics_node(state: AgentState) -> dict:
    result = query_metrics(state["question"])
    chart = generate_chart(result) if result.get("rows") else None
    return {
        "analytics_result": result,
        "chart_b64": chart,
        "answer": result["summary"],
        "citations": [],
    }


def _route_edge(state: AgentState) -> Literal["rag", "analytics"]:
    return state["route"]  # type: ignore[return-value]


def _build() -> object:
    g: StateGraph = StateGraph(AgentState)
    g.add_node("router", _router_node)
    g.add_node("rag", _rag_node)
    g.add_node("analytics", _analytics_node)
    g.add_edge(START, "router")
    g.add_conditional_edges("router", _route_edge, {"rag": "rag", "analytics": "analytics"})
    g.add_edge("rag", END)
    g.add_edge("analytics", END)
    return g.compile()


graph = _build()
