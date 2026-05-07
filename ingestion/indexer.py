import chromadb

from config import get_settings
from ingestion.chunker import Chunk

_client: chromadb.HttpClient | None = None


def _get_client() -> chromadb.HttpClient:
    global _client
    if _client is None:
        settings = get_settings()
        _client = chromadb.HttpClient(host=settings.chroma_host, port=settings.chroma_port)
    return _client


def get_collection(name: str = "regulations") -> chromadb.Collection:
    return _get_client().get_or_create_collection(
        name=name,
        metadata={"hnsw:space": "cosine"},
    )


def index(
    chunks: list[Chunk],
    embeddings: list[list[float]],
    collection_name: str = "regulations",
) -> None:
    collection = get_collection(collection_name)
    collection.upsert(
        ids=[c["id"] for c in chunks],
        documents=[c["text"] for c in chunks],
        embeddings=embeddings,
        metadatas=[c["metadata"] for c in chunks],
    )
