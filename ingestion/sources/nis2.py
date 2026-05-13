from pathlib import Path

from ingestion.models import Document
from ingestion.sources._eurlex import load as _load_eurlex

_URL = "https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=CELEX:32022L2555"
_CACHE_PATH = Path(".cache/nis2/full-text.html")


def load() -> list[Document]:
    return _load_eurlex(url=_URL, cache_path=_CACHE_PATH, regulation="NIS2")
