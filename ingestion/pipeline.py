import time

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from ingestion import chunker, embedder, indexer
from ingestion.sources import dora, gdpr, nis2

console = Console()

_LOADERS = {
    "gdpr": gdpr.load,
    "nis2": nis2.load,
    "dora": dora.load,
}


def run(regulation: str = "gdpr") -> None:
    if regulation not in _LOADERS:
        raise ValueError(f"Unknown regulation '{regulation}'. Choose from: {list(_LOADERS)}")

    with Progress(SpinnerColumn(), TextColumn("{task.description}"), console=console) as progress:
        t = progress.add_task(f"Loading {regulation.upper()} documents...")
        t0 = time.perf_counter()
        documents = _LOADERS[regulation]()
        elapsed = lambda: f"{time.perf_counter() - t0:.1f}s"  # noqa: E731
        desc = f"Loaded {len(documents)} {regulation.upper()} documents [{elapsed()}]"
        progress.update(t, description=desc)
        progress.stop_task(t)

        t = progress.add_task("Chunking documents...")
        t0 = time.perf_counter()
        chunks = chunker.chunk(documents)
        progress.update(t, description=f"Created {len(chunks)} chunks [{elapsed()}]")
        progress.stop_task(t)

        t = progress.add_task(f"Embedding {len(chunks)} chunks via Bedrock Titan...")
        t0 = time.perf_counter()
        texts = [c["text"] for c in chunks]
        embeddings = embedder.embed(texts)
        progress.update(t, description=f"Embedded {len(embeddings)} vectors [{elapsed()}]")
        progress.stop_task(t)

        t = progress.add_task("Indexing into Chroma...")
        t0 = time.perf_counter()
        indexer.index(chunks, embeddings)
        progress.update(t, description=f"Indexed {len(chunks)} chunks [{elapsed()}]")
        progress.stop_task(t)

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
