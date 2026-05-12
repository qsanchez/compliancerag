from typing import Any

import psycopg
from pgvector.psycopg import register_vector

from config import get_settings

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


def ensure_schema(conn: psycopg.Connection[Any]) -> None:
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
