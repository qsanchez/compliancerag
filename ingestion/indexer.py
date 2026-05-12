import json

from ingestion.chunker import Chunk
from vectorstore import client


def index(
    chunks: list[Chunk],
    embeddings: list[list[float]],
    collection_name: str = "regulations",
) -> None:
    with client._get_pgvector_conn() as conn:
        client.ensure_schema(conn)
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
