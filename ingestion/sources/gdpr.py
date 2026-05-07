from pathlib import Path
from typing import TypedDict

import httpx
from bs4 import BeautifulSoup

EURLEX_URL = (
    "https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/"
    "?uri=CELEX%3A32016R0679"
)
CACHE_PATH = Path(".cache/gdpr.html")


class Document(TypedDict):
    id: str
    text: str
    article_number: str
    title: str
    regulation: str
    chapter: str


def _fetch_html() -> str:
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    if CACHE_PATH.exists():
        return CACHE_PATH.read_text(encoding="utf-8")
    with httpx.Client(follow_redirects=True, timeout=60) as client:
        response = client.get(EURLEX_URL)
        response.raise_for_status()
    html = response.text
    CACHE_PATH.write_text(html, encoding="utf-8")
    return html


def _normalize(text: str) -> str:
    return " ".join(text.split())


def load() -> list[Document]:
    html = _fetch_html()
    soup = BeautifulSoup(html, "lxml")
    documents: list[Document] = []
    current_chapter = ""

    for tag in soup.find_all(["p", "div", "h1", "h2", "h3", "h4"]):
        classes = tag.get("class", [])
        text = _normalize(tag.get_text())
        if not text:
            continue

        # Chapter headings
        if any(c in classes for c in ("ti-section-1", "ti-section-2")) or (
            tag.name in ("h2", "h3") and "CHAPTER" in text.upper()
        ):
            current_chapter = text
            continue

        # Article title: look for tags that contain "Article N"
        if any(c in classes for c in ("ti-art", "sti-art")):
            # e.g. "Article 32 - Security of processing"
            parts = text.split("—", 1) if "—" in text else text.split("-", 1)
            article_number = parts[0].strip()
            title = parts[1].strip() if len(parts) > 1 else ""
            # Collect body text from following siblings until next article/chapter
            body_parts: list[str] = []
            for sibling in tag.find_next_siblings(["p", "div"]):
                sib_classes = sibling.get("class", [])
                sib_text = _normalize(sibling.get_text())
                if not sib_text:
                    continue
                _heading = ("ti-art", "sti-art", "ti-section-1", "ti-section-2")
                if any(c in sib_classes for c in _heading):
                    break
                body_parts.append(sib_text)
                if len(" ".join(body_parts)) > 4000:
                    break
            body = " ".join(body_parts).strip()
            if not body:
                continue
            slug = article_number.lower().replace(" ", "-").replace(".", "")
            doc: Document = {
                "id": f"gdpr-{slug}",
                "text": body,
                "article_number": article_number,
                "title": title,
                "regulation": "GDPR",
                "chapter": current_chapter,
            }
            documents.append(doc)

    # Recitals — numbered paragraphs starting with "(N)"
    for tag in soup.find_all(["p", "div"]):
        classes = tag.get("class", [])
        if not any(c in classes for c in ("normal", "recital")):
            continue
        text = _normalize(tag.get_text())
        if not text or len(text) < 50:
            continue
        if text.startswith("(") and ")" in text[:6]:
            closing = text.index(")")
            num_str = text[1:closing]
            if not num_str.isdigit():
                continue
            recital_num = int(num_str)
            body = text[closing + 1 :].strip()
            if not body:
                continue
            doc = {
                "id": f"gdpr-recital-{recital_num}",
                "text": body,
                "article_number": f"Recital {recital_num}",
                "title": "",
                "regulation": "GDPR",
                "chapter": "Recitals",
            }
            documents.append(doc)

    return documents
