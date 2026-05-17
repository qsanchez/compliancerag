"""Online LLM-as-judge evaluator — runs on a sampled fraction of production queries."""

from __future__ import annotations

import random
from typing import TYPE_CHECKING

import boto3
import structlog

from config import get_settings

if TYPE_CHECKING:
    from rag.retriever import RetrievedChunk

logger = structlog.get_logger()

_NAMESPACE = "ComplianceRAG"


def _put_metric(name: str, value: float, environment: str) -> None:
    cw = boto3.client("cloudwatch", region_name=get_settings().aws_region)
    cw.put_metric_data(
        Namespace=f"{_NAMESPACE}/{environment}",
        MetricData=[
            {
                "MetricName": name,
                "Value": value,
                "Unit": "None",
                "Dimensions": [{"Name": "Environment", "Value": environment}],
            }
        ],
    )


def evaluate_sample(
    query: str,
    answer: str,
    chunks: list[RetrievedChunk],
    environment: str = "prod",
) -> None:
    settings = get_settings()
    if random.random() > settings.online_eval_sample_rate:
        return

    context = [c["text"] for c in chunks]
    if not context:
        return

    try:
        from datasets import Dataset
        from ragas import evaluate
        from ragas.metrics import answer_relevancy, faithfulness
    except ImportError:
        logger.debug("online_eval_skipped", reason="ragas/datasets not installed")
        return

    try:
        dataset = Dataset.from_dict(
            {
                "question": [query],
                "answer": [answer],
                "contexts": [context],
            }
        )
        result = evaluate(dataset, metrics=[faithfulness, answer_relevancy])
        scores = result.to_pandas()

        faith = float(scores["faithfulness"].iloc[0])
        relevancy = float(scores["answer_relevancy"].iloc[0])

        _put_metric("OnlineFaithfulness", faith, environment)
        _put_metric("OnlineAnswerRelevancy", relevancy, environment)

        logger.info(
            "online_eval",
            faithfulness=round(faith, 4),
            answer_relevancy=round(relevancy, 4),
        )
    except Exception as exc:
        logger.warning("Online evaluation failed: %s", exc)
