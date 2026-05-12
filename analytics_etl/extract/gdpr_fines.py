"""Download the public GDPR Enforcement Tracker CSV from enforcementtracker.com.

Saves the raw file to analytics_etl/datasets/gdpr_fines_raw.csv.
Run via: task analytics:extract
Prerequisite for: task analytics:load
"""

from pathlib import Path

import httpx
from rich.console import Console

console = Console()

_DATASETS_DIR = Path(__file__).parent.parent / "datasets"
_RAW_CSV_PATH = _DATASETS_DIR / "gdpr_fines_raw.csv"

# enforcementtracker.com exports the full dataset as a CSV download
_DOWNLOAD_URL = "https://www.enforcementtracker.com/?export=csv"

# Column mapping from enforcementtracker export → our canonical schema
_COLUMN_MAP = {
    "Date": "decision_date",
    "Country": "country",
    "Authority": "authority",
    "Fine (EUR)": "fine_amount_eur",
    "Controller/Processor": "controller",
    "Sector": "sector",
    "Quoted Art.": "articles_violated",
    "Type": "violation_type",
    "Summary": "summary",
}


def download(url: str = _DOWNLOAD_URL, dest: Path = _RAW_CSV_PATH) -> Path:
    """Fetch the CSV from enforcementtracker.com and save to dest."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    with httpx.stream("GET", url, follow_redirects=True, timeout=60) as response:
        response.raise_for_status()
        with dest.open("wb") as f:
            for chunk in response.iter_bytes(chunk_size=65536):
                f.write(chunk)
    return dest


def normalise(raw_path: Path = _RAW_CSV_PATH, dest: Path = _RAW_CSV_PATH) -> Path:
    """Rename columns to match our schema and drop unneeded ones in-place."""
    import pandas as pd

    df = pd.read_csv(raw_path, encoding="utf-8", on_bad_lines="skip")

    # Keep only columns we have a mapping for
    available = {k: v for k, v in _COLUMN_MAP.items() if k in df.columns}
    df = df[list(available.keys())].rename(columns=available)

    # Ensure all schema columns exist (fill missing with empty string)
    for col in _COLUMN_MAP.values():
        if col not in df.columns:
            df[col] = ""

    df.to_csv(dest, index=False, encoding="utf-8")
    return dest


def run(url: str = _DOWNLOAD_URL) -> Path:
    console.print(f"[bold]Downloading GDPR fines CSV from[/] [cyan]{url}[/]")
    raw_path = download(url)
    size_kb = raw_path.stat().st_size // 1024
    console.print(f"  Saved to [cyan]{raw_path}[/] ({size_kb} KB)")

    console.print("[bold]Normalising column names...[/]")
    normalise(raw_path)
    console.print(f"  Done — [cyan]{raw_path}[/] ready for [bold]task analytics:load[/]")
    return raw_path


if __name__ == "__main__":
    run()
