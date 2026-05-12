"""Download GDPR fines data from the enforcementtracker.com internal JSON feed.

Saves normalised data to analytics_etl/datasets/gdpr_fines_raw.csv.
Run via: task analytics:extract
Prerequisite for: task analytics:load
"""

import re
from pathlib import Path

import httpx
import pandas as pd
from rich.console import Console

console = Console()

_DATASETS_DIR = Path(__file__).parent.parent / "datasets"
_RAW_CSV_PATH = _DATASETS_DIR / "gdpr_fines_raw.csv"

# Internal DataTables JSON feed — returns all rows as a {"data": [[...]]} object
_JSON_URL = "https://www.enforcementtracker.com/data4sfk3j4hwe324kjhfdwe.json"

# Column positions in each row array (13 elements per row)
_COL_COUNTRY = 2
_COL_AUTHORITY = 3
_COL_DATE = 4
_COL_FINE = 5
_COL_CONTROLLER = 6
_COL_SECTOR = 7
_COL_ARTICLES = 8
_COL_TYPE = 9
_COL_SUMMARY = 10


def _extract_country(raw: str) -> str:
    """Strip HTML img tag and extract the country name text."""
    return re.sub(r"<[^>]+>", "", raw).strip()


def _parse_fine(raw: str) -> int:
    """Convert '4,800' or '50,000,000' to integer."""
    cleaned = re.sub(r"[^\d]", "", raw)
    return int(cleaned) if cleaned else 0


def fetch(url: str = _JSON_URL) -> list[dict]:
    response = httpx.get(url, follow_redirects=True, timeout=60)
    response.raise_for_status()
    rows = response.json()["data"]
    return [
        {
            "decision_date": row[_COL_DATE],
            "country": _extract_country(row[_COL_COUNTRY]),
            "authority": row[_COL_AUTHORITY],
            "fine_amount_eur": _parse_fine(row[_COL_FINE]),
            "controller": row[_COL_CONTROLLER],
            "sector": row[_COL_SECTOR],
            "articles_violated": row[_COL_ARTICLES],
            "violation_type": row[_COL_TYPE],
            "summary": row[_COL_SUMMARY],
        }
        for row in rows
    ]


def run(url: str = _JSON_URL) -> Path:
    console.print(f"[bold]Fetching GDPR fines JSON from[/] [cyan]{url}[/]")
    records = fetch(url)
    console.print(f"  Retrieved [green]{len(records)}[/] fines")

    _RAW_CSV_PATH.parent.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(records)
    df.to_csv(_RAW_CSV_PATH, index=False, encoding="utf-8")
    size_kb = _RAW_CSV_PATH.stat().st_size // 1024
    console.print(f"  Saved to [cyan]{_RAW_CSV_PATH}[/] ({size_kb} KB)")
    console.print("  Ready for [bold]task analytics:load[/]")
    return _RAW_CSV_PATH


if __name__ == "__main__":
    run()
