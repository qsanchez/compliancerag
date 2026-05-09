import re
import time
from pathlib import Path
from typing import TypedDict

import httpx
from bs4 import BeautifulSoup

# Source: gdpr-info.eu — EUR-Lex blocks programmatic access via AWS WAF.
# gdpr-info.eu republishes the official text structured by article, which
# is ideal for our per-article chunking strategy.
BASE_URL = "https://gdpr-info.eu"
CACHE_DIR = Path(".cache/gdpr")
_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; compliancerag-ingestion/1.0)"}
_REQUEST_DELAY = 0.5  # seconds between requests to be polite


class Document(TypedDict):
    id: str
    text: str
    article_number: str
    title: str
    regulation: str
    chapter: str


def _normalize(text: str) -> str:
    return " ".join(text.split())


def _fetch(client: httpx.Client, url: str, cache_path: Path) -> str:
    if cache_path.exists() and cache_path.stat().st_size > 0:
        return cache_path.read_text(encoding="utf-8")
    time.sleep(_REQUEST_DELAY)
    response = client.get(url)
    response.raise_for_status()
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(response.text, encoding="utf-8")
    return response.text


def _parse_article(html: str, chapter: str) -> Document | None:
    soup = BeautifulSoup(html, "lxml")

    h1 = soup.find("h1", class_="entry-title")
    if not h1:
        return None

    number_span = h1.find("span", class_="dsgvo-number")
    title_span = h1.find("span", class_="dsgvo-title")
    article_number = _normalize(number_span.get_text()) if number_span else ""
    title = _normalize(title_span.get_text()) if title_span else ""

    content_div = soup.find("div", class_="entry-content")
    if not content_div:
        return None

    # Remove nav / recital suggestion blocks — keep only the normative text
    for tag in content_div.find_all(
        class_=["empfehlung-erwaegungsgruende", "page-navigation", "link-to-overview", "feedback"]
    ):
        tag.decompose()

    text = _normalize(content_div.get_text())
    if not text:
        return None

    slug = re.sub(r"[^a-z0-9]+", "-", article_number.lower()).strip("-")
    return Document(
        id=f"gdpr-{slug}",
        text=text,
        article_number=article_number,
        title=title,
        regulation="GDPR",
        chapter=chapter,
    )


def _parse_recital(html: str, recital_num: int) -> Document | None:
    soup = BeautifulSoup(html, "lxml")
    content_div = soup.find("div", class_="entry-content")
    if not content_div:
        return None
    for tag in content_div.find_all(class_=["page-navigation", "link-to-overview", "feedback"]):
        tag.decompose()
    text = _normalize(content_div.get_text())
    if not text:
        return None
    return Document(
        id=f"gdpr-recital-{recital_num}",
        text=text,
        article_number=f"Recital {recital_num}",
        title="",
        regulation="GDPR",
        chapter="Recitals",
    )


def _get_article_index(client: httpx.Client) -> list[tuple[str, str]]:
    """Return list of (article_url, chapter_name) from the table of contents."""
    html = _fetch(client, BASE_URL + "/", CACHE_DIR / "index.html")
    soup = BeautifulSoup(html, "lxml")

    toc = soup.find("h2", string=re.compile("Table of Contents"))
    if not toc:
        raise RuntimeError("Could not find Table of Contents on gdpr-info.eu")

    container = toc.find_next_sibling()
    entries: list[tuple[str, str]] = []
    current_chapter = ""

    for div in container.find_all("div", recursive=False):
        classes = div.get("class", [])
        if "kapitel" in classes:
            num_tag = div.find("span", class_="nummer")
            title_tag = div.find("span", class_="titel")
            num = _normalize(num_tag.get_text()) if num_tag else ""
            title = _normalize(title_tag.get_text()) if title_tag else ""
            current_chapter = f"{num} — {title}" if num and title else num or title
        elif "artikel" in classes:
            link = div.find("a", href=True)
            if link and current_chapter:
                entries.append((link["href"], current_chapter))

    return entries


def load(include_recitals: bool = True) -> list[Document]:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    documents: list[Document] = []

    with httpx.Client(follow_redirects=True, timeout=30, headers=_HEADERS) as client:
        # Articles
        index = _get_article_index(client)
        seen_urls: set[str] = set()
        for url, chapter in index:
            if url in seen_urls:
                continue
            seen_urls.add(url)
            slug = url.rstrip("/").split("/")[-1]
            cache_path = CACHE_DIR / f"{slug}.html"
            try:
                html = _fetch(client, url, cache_path)
                doc = _parse_article(html, chapter)
                if doc:
                    documents.append(doc)
            except Exception:
                continue

        # Recitals (1–173)
        if include_recitals:
            for n in range(1, 174):
                url = f"{BASE_URL}/recitals/no-{n}/"
                cache_path = CACHE_DIR / f"recital-{n}.html"
                try:
                    html = _fetch(client, url, cache_path)
                    doc = _parse_recital(html, n)
                    if doc:
                        documents.append(doc)
                except Exception:
                    continue

    return documents
