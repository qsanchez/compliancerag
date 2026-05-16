import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from datasets import Dataset
from langchain_community.chat_models import ChatLiteLLM
from langchain_core.embeddings import Embeddings
from ragas import evaluate
from ragas.embeddings import LangchainEmbeddingsWrapper
from ragas.llms import LangchainLLMWrapper
from ragas.metrics import answer_relevancy, context_precision, context_recall, faithfulness
from rich.console import Console
from rich.table import Table

from config import get_settings
from rag import pipeline
from vectorstore import embedder

console = Console()

GOLDEN_DATASET_PATH = Path(__file__).parent / "golden_dataset.json"
REPORTS_DIR = Path(__file__).parent / "reports"


def _detect_regulations(golden: list[dict]) -> list[str]:
    found = set()
    for item in golden:
        q = item["question"].lower()
        if "gdpr" in q:
            found.add("GDPR")
        if "nis2" in q or "nis 2" in q:
            found.add("NIS2")
        if "dora" in q:
            found.add("DORA")
    return sorted(found)


class _TitanEmbeddings(Embeddings):
    """LangChain embeddings wrapper backed by our Bedrock Titan embedder."""

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return embedder.embed(texts)

    def embed_query(self, text: str) -> list[float]:
        return embedder.embed([text])[0]

    def __call__(self, *args: Any, **kwargs: Any) -> Any:  # satisfies abstract method variants
        return self.embed_documents(*args, **kwargs)


def _make_ragas_llm() -> LangchainLLMWrapper:
    settings = get_settings()
    # ChatLiteLLM routes through LiteLLM so we stay model-agnostic
    return LangchainLLMWrapper(ChatLiteLLM(model=settings.litellm_model))


def run() -> None:
    parser = argparse.ArgumentParser(description="Run RAGAS evaluation")
    parser.add_argument(
        "--label",
        default="eval",
        help="Run label used in the report filename and metadata (e.g. phase_1, phase_2)",
    )
    args, _ = parser.parse_known_args()

    golden = json.loads(GOLDEN_DATASET_PATH.read_text())
    console.print(
        f"[bold]Running RAGAS evaluation on {len(golden)} questions (label: {args.label})...[/]"
    )

    questions: list[str] = []
    answers: list[str] = []
    contexts: list[list[str]] = []
    ground_truths: list[str] = []

    for i, item in enumerate(golden, start=1):
        q = item["question"]
        console.print(f"  [{i}/{len(golden)}] {q[:80]}...")
        result = pipeline.run(q)

        questions.append(q)
        answers.append(result["answer"])
        contexts.append([c["text"] for c in result["chunks"]])
        ground_truths.append(item["ground_truth"])

    dataset = Dataset.from_dict(
        {
            "question": questions,
            "answer": answers,
            "contexts": contexts,
            "ground_truth": ground_truths,
        }
    )

    ragas_llm = _make_ragas_llm()
    ragas_embeddings = LangchainEmbeddingsWrapper(_TitanEmbeddings())

    result = evaluate(
        dataset,
        metrics=[faithfulness, answer_relevancy, context_precision, context_recall],
        llm=ragas_llm,
        embeddings=ragas_embeddings,
    )

    # Print summary table
    table = Table(title="RAGAS Evaluation Results")
    table.add_column("Metric", style="cyan")
    table.add_column("Score", style="bold")
    scores = result.to_pandas().select_dtypes(include="number").mean()
    for metric, score in scores.items():
        color = "green" if score >= 0.7 else "red"
        table.add_row(str(metric), f"[{color}]{score:.3f}[/{color}]")
    console.print(table)

    # Save report
    REPORTS_DIR.mkdir(exist_ok=True)
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    report_path = REPORTS_DIR / f"{args.label}_{timestamp}.json"
    settings = get_settings()
    report = {
        "label": args.label,
        "timestamp": timestamp,
        "num_questions": len(golden),
        "regulations": _detect_regulations(golden),
        "retrieval": {
            "reranker_enabled": settings.reranker_enabled,
            "reranker_model": settings.bedrock_model_id if settings.reranker_enabled else None,
        },
        "model": settings.bedrock_model_id,
        "scores": {str(k): float(v) for k, v in scores.items()},
    }
    report_path.write_text(json.dumps(report, indent=2))
    console.print(f"\nReport saved to [bold]{report_path}[/]")

    faithfulness_score = float(scores.get("faithfulness", 0.0))
    if faithfulness_score < 0.7:
        console.print(
            f"[bold red]FAIL:[/] faithfulness {faithfulness_score:.3f} < 0.7"
            " (exit criterion not met)"
        )
        sys.exit(1)
    else:
        console.print(f"[bold green]PASS:[/] faithfulness {faithfulness_score:.3f} >= 0.7")


if __name__ == "__main__":
    run()
