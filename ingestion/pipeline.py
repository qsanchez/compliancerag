import time

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from ingestion import chunker, embedder, indexer
from ingestion.sources import gdpr

console = Console()


def run(regulation: str = "gdpr") -> None:
    if regulation != "gdpr":
        raise ValueError(f"Unsupported regulation in Phase 1: {regulation}")

    with Progress(SpinnerColumn(), TextColumn("{task.description}"), console=console) as progress:
        t = progress.add_task("Loading GDPR documents from EUR-Lex...")
        t0 = time.perf_counter()
        documents = gdpr.load()
        elapsed = lambda: f"{time.perf_counter() - t0:.1f}s"  # noqa: E731
        progress.update(t, description=f"Loaded {len(documents)} documents [{elapsed()}]")
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
    parser.add_argument("--regulation", default="gdpr", help="Regulation to ingest (default: gdpr)")
    args = parser.parse_args()
    run(args.regulation)
