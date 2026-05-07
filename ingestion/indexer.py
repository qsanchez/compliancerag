import json
from typing import Any

import chromadb
import psycopg
from pgvector.psycopg import register_vector

from config import get_settings
from ingestion.chunker import Chunk

# ── Chroma backend ────────────────────────────────────────────────────────────

_chroma_client: chromadb.ClientAPI | None = None


def _get_chroma_client() -> chromadb.ClientAPI:
    global _chroma_client
    if _chroma_client is None:
        settings = get_settings()
        _chroma_client = chromadb.HttpClient(host=settings.chroma_host, port=settings.chroma_port)
    return _chroma_client


def get_collection(name: str = "regulations") -> chromadb.Collection:
    return _get_chroma_client().get_or_create_collection(
        name=name,
        metadata={"hnsw:space": "cosine"},
    )


def _index_chroma(
    chunks: list[Chunk],
    embeddings: list[list[float]],
    collection_name: str,
) -> None:
    collection = get_collection(collection_name)
    collection.upsert(
        ids=[c["id"] for c in chunks],
        documents=[c["text"] for c in chunks],
        embeddings=embeddings,
        metadatas=[c["metadata"] for c in chunks],
    )


# ── pgvector backend ──────────────────────────────────────────────────────────

_EMBEDDING_DIM = 1024  # Amazon Titan Embeddings v2 default


def _get_pgvector_conn() -> psycopg.Connection[Any]:
    conn = psycopg.connect(get_settings().database_url)
    # Both extensions must exist before register_vector maps the vector type
    with conn.cursor() as cur:
        cur.execute("CREATE EXTENSION IF NOT EXISTS vector")
        cur.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    conn.commit()
    register_vector(conn)
    return conn


def _ensure_pgvector_schema(conn: psycopg.Connection[Any]) -> None:
    with conn.cursor() as cur:
        cur.execute(f"""
            CREATE TABLE IF NOT EXISTS embeddings (
                id       TEXT PRIMARY KEY,
                document TEXT NOT NULL,
                embedding VECTOR({_EMBEDDING_DIM}),
                metadata JSONB
            )
        """)
        # HNSW index for fast ANN with cosine distance (semantic search)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS embeddings_hnsw
            ON embeddings USING hnsw (embedding vector_cosine_ops)
        """)
        # GIN trigram index for keyword search (pg_trgm word_similarity)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS embeddings_trgm
            ON embeddings USING gin (document gin_trgm_ops)
        """)
    conn.commit()


def _index_pgvector(
    chunks: list[Chunk],
    embeddings: list[list[float]],
) -> None:
    with _get_pgvector_conn() as conn:
        _ensure_pgvector_schema(conn)
        with conn.cursor() as cur:
            for chunk, vec in zip(chunks, embeddings):
                cur.execute(
                    """
                    INSERT INTO embeddings (id, document, embedding, metadata)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (id) DO UPDATE SET
                        document  = EXCLUDED.document,
                        embedding = EXCLUDED.embedding,
                        metadata  = EXCLUDED.metadata
                    """,
                    (chunk["id"], chunk["text"], vec, json.dumps(chunk["metadata"])),
                )
        conn.commit()


# ── Public interface ──────────────────────────────────────────────────────────

def index(
    chunks: list[Chunk],
    embeddings: list[list[float]],
    collection_name: str = "regulations",
) -> None:
    settings = get_settings()
    if settings.vector_store == "pgvector":
        _index_pgvector(chunks, embeddings)
    else:
        _index_chroma(chunks, embeddings, collection_name)
