from unittest.mock import patch

from agent.graph import graph
from agent.state import AgentState

_RAG_ANSWER = "Article 32 requires appropriate security measures."
_RAG_CITATION = "Art. 32, GDPR"


def _initial_state(question: str) -> AgentState:
    return {
        "question": question,
        "history": [],
        "route": None,
        "analytics_result": None,
        "chart_b64": None,
        "answer": "",
        "citations": [],
    }


@patch("agent.graph.classify", return_value="rag")
@patch(
    "agent.graph.pipeline.run",
    return_value={"answer": _RAG_ANSWER, "citations": [_RAG_CITATION], "chunks": []},
)
def test_rag_path_sets_answer_and_citations(mock_run, mock_classify) -> None:
    result = graph.invoke(_initial_state("What does Article 32 require?"))

    assert result["route"] == "rag"
    assert result["answer"] == _RAG_ANSWER
    assert result["citations"] == [_RAG_CITATION]


@patch("agent.graph.classify", return_value="rag")
@patch(
    "agent.graph.pipeline.run",
    return_value={"answer": _RAG_ANSWER, "citations": [], "chunks": []},
)
def test_rag_path_calls_search_with_question(mock_run, mock_classify) -> None:
    question = "What does Article 32 require?"
    graph.invoke(_initial_state(question))
    mock_run.assert_called_once_with(question, history=[])


@patch("agent.graph.classify", return_value="analytics")
@patch("agent.graph.generate_chart", return_value=None)
@patch(
    "agent.graph.query_metrics",
    return_value={"summary": "In 2023, 45 fines were issued.", "rows": [], "sql": "SELECT ..."},
)
def test_analytics_path_sets_answer(mock_metrics, mock_chart, mock_classify) -> None:
    result = graph.invoke(_initial_state("How many GDPR fines in 2023?"))

    assert result["route"] == "analytics"
    assert result["answer"] == "In 2023, 45 fines were issued."
    assert result["citations"] == []


@patch("agent.graph.classify", return_value="analytics")
@patch("agent.graph.generate_chart", return_value="base64encodedpng==")
@patch(
    "agent.graph.query_metrics",
    return_value={
        "summary": "Fines increased year on year.",
        "rows": [{"year": "2022", "total_eur": "1000000"}],
        "sql": "SELECT ...",
    },
)
def test_analytics_path_includes_chart_when_rows_present(
    mock_metrics, mock_chart, mock_classify
) -> None:
    result = graph.invoke(_initial_state("Show me fine trends by year"))

    assert result["chart_b64"] == "base64encodedpng=="


@patch("agent.graph.classify", return_value="rag")
@patch(
    "agent.graph.pipeline.run",
    return_value={
        "answer": "DORA requires ICT risk management.",
        "citations": ["Art. 6, DORA"],
        "chunks": [],
    },
)
def test_history_passed_to_pipeline(mock_run, mock_classify) -> None:
    state = _initial_state("What else does it require?")
    state["history"] = [
        {"role": "user", "content": "What is DORA?"},
        {"role": "assistant", "content": "DORA is the Digital Operational Resilience Act."},
    ]
    graph.invoke(state)
    assert len(mock_run.call_args.kwargs["history"]) == 2
