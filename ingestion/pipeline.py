import time
from collections.abc import Generator
from contextlib import contextmanager

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TaskID, TextColumn

from ingestion import chunker, indexer
from ingestion.sources import dora, gdpr, nis2
from vectorstore import embedder

console = Console()

_LOADERS = {
    "gdpr": gdpr.load,
    "nis2": nis2.load,
    "dora": dora.load,
}


@contextmanager
def _step(progress: Progress, msg: str) -> Generator:
    t: TaskID = progress.add_task(msg)
    t0 = time.perf_counter()

    def done(result: str) -> None:
        progress.update(t, description=f"{result} [{time.perf_counter() - t0:.1f}s]")

    yield done
    progress.stop_task(t)


def run(regulation: str = "gdpr") -> None:
    if regulation not in _LOADERS:
        raise ValueError(f"Unknown regulation '{regulation}'. Choose from: {list(_LOADERS)}")

    with Progress(SpinnerColumn(), TextColumn("{task.description}"), console=console) as progress:
        with _step(progress, f"Loading {regulation.upper()} documents...") as done:
            documents = _LOADERS[regulation]()
            done(f"Loaded {len(documents)} {regulation.upper()} documents")

        with _step(progress, "Chunking documents...") as done:
            chunks = chunker.chunk(documents)
            done(f"Created {len(chunks)} chunks")

        with _step(progress, f"Embedding {len(chunks)} chunks via Bedrock Titan...") as done:
            embeddings = embedder.embed([c["text"] for c in chunks])
            done(f"Embedded {len(embeddings)} vectors")

        with _step(progress, "Indexing...") as done:
            indexer.index(chunks, embeddings)
            done(f"Indexed {len(chunks)} chunks")

    console.print(f"[bold green]Done.[/] {len(chunks)} chunks indexed for {regulation.upper()}.")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Run the ingestion pipeline.")
    parser.add_argument(
        "--regulation",
        default="gdpr",
        choices=list(_LOADERS),
        help="Regulation to ingest (default: gdpr)",
    )
    args = parser.parse_args()
    run(args.regulation)
