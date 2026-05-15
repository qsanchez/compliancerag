from __future__ import annotations

import boto3
from langsmith import traceable

from config import get_settings
from rag.retriever import RetrievedChunk

# Candidates multiplier: fetch this many chunks from the retriever before reranking.
FETCH_MULTIPLIER = 3


@traceable(name="rerank", run_type="chain")
def rerank(query: str, chunks: list[RetrievedChunk], top_k: int) -> list[RetrievedChunk]:
    if not chunks:
        return chunks
    settings = get_settings()
    client = boto3.client("bedrock-agent-runtime", region_name=settings.aws_region)

    sources = [
        {
            "inlineDocumentSource": {
                "textDocument": {"text": chunk["text"]},
                "type": "TEXT",
            },
            "type": "INLINE",
        }
        for chunk in chunks
    ]

    model_id = settings.reranker_model
    model_arn = (
        model_id
        if model_id.startswith("arn:")
        else f"arn:aws:bedrock:{settings.aws_region}::foundation-model/{model_id}"
    )

    response = client.rerank(
        queries=[{"textQuery": {"text": query}, "type": "TEXT"}],
        rerankingConfiguration={
            "bedrockRerankingConfiguration": {
                "modelConfiguration": {"modelArn": model_arn},
                "numberOfResults": top_k,
            },
            "type": "BEDROCK_RERANKING_MODEL",
        },
        sources=sources,
    )

    return [
        RetrievedChunk(
            text=chunks[item["index"]]["text"],
            metadata=chunks[item["index"]]["metadata"],
            score=item["relevanceScore"],
        )
        for item in response.get("rerankingResults", [])
    ]
