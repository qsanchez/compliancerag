import re
import time
import warnings
from pathlib import Path

import httpx

from ingestion.types import Document

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
}
_REQUEST_DELAY = 1.0


def _normalize(text: str) -> str:
    return " ".join(text.split())


def _fetch(url: str, cache_path: Path) -> str:
    if cache_path.exists() and cache_path.stat().st_size > 0:
        return cache_path.read_text(encoding="utf-8")
    time.sleep(_REQUEST_DELAY)
    with httpx.Client(follow_redirects=True, timeout=30, headers=_HEADERS) as client:
        response = client.get(url)
        response.raise_for_status()
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(response.text, encoding="utf-8")
    return response.text


def _parse_full_text(html: str, regulation: str) -> list[Document]:
    """Parse EUR-Lex full-text HTML into one Document per article.

    EUR-Lex HTML uses:
      p.oj-ti-section-1  — chapter number (CHAPTER I, CHAPTER II, ...)
      p.oj-ti-section-2  — chapter name (General provisions, ...)
      div.eli-subdivision containing p.oj-ti-art — one article each
      div.eli-title       — article subtitle inside the subdivision
    """
    from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning  # noqa: PLC0415

    warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)
    soup = BeautifulSoup(html, "lxml")
    documents: list[Document] = []

    current_chapter_num = ""
    current_chapter_name = ""

    # Collect relevant nodes in document order: chapter headings + article subdivisions
    def _is_relevant(tag: object) -> bool:
        cls = tag.get("class") or []
        if tag.name == "p" and ("oj-ti-section-1" in cls or "oj-ti-section-2" in cls):
            return True
        if tag.name == "div" and "eli-subdivision" in cls:
            # Only article subdivisions (those with a direct p.oj-ti-art child)
            return bool(tag.find("p", class_="oj-ti-art", recursive=False))
        return False

    for el in soup.find_all(_is_relevant):
        cls = el.get("class", [])

        if "oj-ti-section-1" in cls:
            current_chapter_num = _normalize(el.get_text())
            current_chapter_name = ""  # reset — oj-ti-section-2 fills it next
            continue

        if "oj-ti-section-2" in cls:
            current_chapter_name = _normalize(el.get_text())
            continue

        # Article subdivision
        art_heading = el.find("p", class_="oj-ti-art", recursive=False)
        title_el = el.find("div", class_="eli-title", recursive=False)

        article_number = _normalize(art_heading.get_text()).replace("\xa0", " ")
        title = _normalize(title_el.get_text()) if title_el else ""

        # Body text: all content except the heading and title elements
        body_parts: list[str] = []
        for child in el.children:
            if not hasattr(child, "name") or not child.name:
                continue
            child_cls = child.get("class") or []
            if "oj-ti-art" in child_cls or "eli-title" in child_cls:
                continue
            part = _normalize(child.get_text())
            if part:
                body_parts.append(part)

        body = " ".join(body_parts)
        if not body:
            continue

        chapter = current_chapter_num
        if current_chapter_name:
            chapter = f"{current_chapter_num} — {current_chapter_name}"

        slug = re.sub(r"[^a-z0-9]+", "-", article_number.lower()).strip("-")
        reg_slug = re.sub(r"[^a-z0-9]+", "-", regulation.lower()).strip("-")

        documents.append(
            Document(
                id=f"{reg_slug}-{slug}",
                text=f"{article_number} {title} {body}".strip(),
                article_number=article_number,
                title=title,
                regulation=regulation,
                chapter=chapter,
            )
        )

    return documents


def load(url: str, cache_path: Path, regulation: str) -> list[Document]:
    html = _fetch(url, cache_path)
    return _parse_full_text(html, regulation)
