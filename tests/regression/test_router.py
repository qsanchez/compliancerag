from unittest.mock import MagicMock, patch

from agent.router import classify


def _mock_completion(content: str) -> MagicMock:
    response = MagicMock()
    response.choices[0].message.content = content
    return response


@patch("agent.router.litellm.completion")
def test_regulatory_question_routes_to_rag(mock_completion: MagicMock) -> None:
    mock_completion.return_value = _mock_completion("rag")
    assert classify("What does Article 32 of GDPR require?") == "rag"


@patch("agent.router.litellm.completion")
def test_analytics_question_routes_to_analytics(mock_completion: MagicMock) -> None:
    mock_completion.return_value = _mock_completion("analytics")
    assert classify("How many GDPR fines were issued in 2023?") == "analytics"


@patch("agent.router.litellm.completion")
def test_nis2_question_routes_to_rag(mock_completion: MagicMock) -> None:
    mock_completion.return_value = _mock_completion("rag")
    assert classify("What are the NIS2 incident reporting timelines?") == "rag"


@patch("agent.router.litellm.completion")
def test_fine_trend_question_routes_to_analytics(mock_completion: MagicMock) -> None:
    mock_completion.return_value = _mock_completion("analytics")
    assert classify("What is the trend of GDPR fines in Spain over 3 years?") == "analytics"


@patch("agent.router.litellm.completion")
def test_ambiguous_response_defaults_to_rag(mock_completion: MagicMock) -> None:
    mock_completion.return_value = _mock_completion("unknown")
    assert classify("something ambiguous") == "rag"


@patch("agent.router.litellm.completion")
def test_empty_response_defaults_to_rag(mock_completion: MagicMock) -> None:
    mock_completion.return_value = _mock_completion("")
    assert classify("what is gdpr") == "rag"


@patch("agent.router.litellm.completion")
def test_router_passes_question_to_llm(mock_completion: MagicMock) -> None:
    mock_completion.return_value = _mock_completion("rag")
    question = "What is the right to erasure?"
    classify(question)
    call_messages = mock_completion.call_args[1]["messages"]
    user_message = next(m for m in call_messages if m["role"] == "user")
    assert user_message["content"] == question


@patch("agent.router.litellm.completion")
def test_router_uses_zero_temperature(mock_completion: MagicMock) -> None:
    mock_completion.return_value = _mock_completion("rag")
    classify("What is GDPR?")
    assert mock_completion.call_args[1]["temperature"] == 0.0
