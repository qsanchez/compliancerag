from unittest.mock import MagicMock, patch

from ingestion.embedder import embed


def _make_mock_response(n: int) -> MagicMock:
    response = MagicMock()
    response.data = [{"embedding": [0.1, 0.2, 0.3]} for _ in range(n)]
    return response


@patch("ingestion.embedder.litellm.embedding")
def test_embed_single_text(mock_embedding: MagicMock) -> None:
    mock_embedding.return_value = _make_mock_response(1)
    result = embed(["hello world"])
    assert len(result) == 1
    assert result[0] == [0.1, 0.2, 0.3]
    mock_embedding.assert_called_once()


@patch("ingestion.embedder.litellm.embedding")
def test_embed_batches_when_over_limit(mock_embedding: MagicMock) -> None:
    # 25 texts should produce ceil(25/10) = 3 calls
    mock_embedding.side_effect = [
        _make_mock_response(10),
        _make_mock_response(10),
        _make_mock_response(5),
    ]
    texts = [f"text {i}" for i in range(25)]
    result = embed(texts)
    assert len(result) == 25
    assert mock_embedding.call_count == 3


@patch("ingestion.embedder.litellm.embedding")
def test_embed_exactly_batch_size(mock_embedding: MagicMock) -> None:
    mock_embedding.return_value = _make_mock_response(10)
    texts = [f"text {i}" for i in range(10)]
    result = embed(texts)
    assert len(result) == 10
    assert mock_embedding.call_count == 1


@patch("ingestion.embedder.litellm.embedding")
def test_embed_empty_list(mock_embedding: MagicMock) -> None:
    result = embed([])
    assert result == []
    mock_embedding.assert_not_called()


@patch("ingestion.embedder.litellm.embedding")
def test_embed_uses_correct_model(mock_embedding: MagicMock) -> None:
    mock_embedding.return_value = _make_mock_response(1)
    embed(["test"])
    call_kwargs = mock_embedding.call_args
    model_used = call_kwargs[1].get("model") or call_kwargs[0][0]
    assert "titan-embed" in model_used or "bedrock" in model_used
