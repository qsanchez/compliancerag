from pathlib import Path

from ingestion.sources._eurlex import load as _load_eurlex
from ingestion.sources.gdpr import Document

_URL = "https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=CELEX:32022R2554"
_CACHE_PATH = Path(".cache/dora/full-text.html")


def load() -> list[Document]:
    return _load_eurlex(url=_URL, cache_path=_CACHE_PATH, regulation="DORA")
