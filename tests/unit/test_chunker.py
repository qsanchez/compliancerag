import tiktoken

from ingestion.chunker import chunk
from ingestion.sources.gdpr import Document

_ENC = tiktoken.get_encoding("cl100k_base")


def _make_doc(text: str, article: str = "Article 32") -> Document:
    return Document(
        id=f"gdpr-art-{article.lower().replace(' ', '-')}",
        text=text,
        article_number=article,
        title="Test Article",
        regulation="GDPR",
        chapter="Chapter IV",
    )


def test_short_text_produces_one_chunk() -> None:
    doc = _make_doc("This is a short text.")
    result = chunk([doc], chunk_size=512, overlap=50)
    assert len(result) == 1
    assert result[0]["text"] == "This is a short text."


def test_long_text_splits_into_multiple_chunks() -> None:
    # ~700 tokens of text — should split at 512
    word = "compliance " * 700
    doc = _make_doc(word.strip())
    result = chunk([doc], chunk_size=512, overlap=50)
    assert len(result) >= 2


def test_each_chunk_within_token_limit() -> None:
    word = "data protection regulation " * 300
    doc = _make_doc(word.strip())
    result = chunk([doc], chunk_size=200, overlap=20)
    for c in result:
        token_count = len(_ENC.encode(c["text"]))
        assert token_count <= 200, f"Chunk exceeds limit: {token_count} tokens"


def test_metadata_preserved_on_chunks() -> None:
    doc = _make_doc("Personal data shall be processed lawfully.", article="Article 5")
    result = chunk([doc])
    assert len(result) >= 1
    for c in result:
        assert c["metadata"]["article_number"] == "Article 5"
        assert c["metadata"]["regulation"] == "GDPR"
        assert c["metadata"]["chapter"] == "Chapter IV"


def test_chunk_ids_are_unique() -> None:
    doc = _make_doc("word " * 600)
    result = chunk([doc], chunk_size=100, overlap=10)
    ids = [c["id"] for c in result]
    assert len(ids) == len(set(ids))


def test_multiple_documents() -> None:
    docs = [_make_doc("short text", article=f"Article {i}") for i in range(5)]
    result = chunk(docs)
    assert len(result) == 5
    regulations = {c["metadata"]["regulation"] for c in result}
    assert regulations == {"GDPR"}
