from typing import Literal

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from agent.router import classify
from agent.state import AgentState
from analytics_query.generate_chart import generate_chart
from analytics_query.query_metrics import query_metrics
from rag import pipeline


def _router_node(state: AgentState) -> dict:
    return {"route": classify(state["question"])}


def _rag_node(state: AgentState) -> dict:
    result = pipeline.run(state["question"], history=state.get("history"))
    return {
        "answer": result["answer"],
        "citations": result["citations"],
        "chunks": result["chunks"],
    }


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


def _build() -> CompiledStateGraph:
    g: StateGraph = StateGraph(AgentState)
    g.add_node("router", _router_node)
    g.add_node("rag", _rag_node)
    g.add_node("analytics", _analytics_node)
    g.add_edge(START, "router")
    g.add_conditional_edges("router", _route_edge, {"rag": "rag", "analytics": "analytics"})
    g.add_edge("rag", END)
    g.add_edge("analytics", END)
    return g.compile()


graph: CompiledStateGraph = _build()
