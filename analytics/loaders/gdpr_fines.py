"""Load GDPR fines CSV → Parquet locally, then upload to S3 for Athena."""

from pathlib import Path

import boto3
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from rich.console import Console

from analytics.schemas.gdpr_fines import SCHEMA
from config import get_settings

console = Console()

_DATASETS_DIR = Path(__file__).parent.parent / "datasets"
_CSV_PATH = _DATASETS_DIR / "gdpr_fines_sample.csv"
_PARQUET_PATH = _DATASETS_DIR / "gdpr_fines.parquet"
_S3_KEY = "analytics/gdpr_fines/gdpr_fines.parquet"


def csv_to_parquet(csv_path: Path = _CSV_PATH, parquet_path: Path = _PARQUET_PATH) -> Path:
    df = pd.read_csv(csv_path)
    df["decision_date"] = pd.to_datetime(df["decision_date"], errors="coerce").dt.date
    df["fine_amount_eur"] = (
        pd.to_numeric(df["fine_amount_eur"], errors="coerce").fillna(0).astype(int)
    )
    str_cols = (
        "country",
        "authority",
        "controller",
        "sector",
        "articles_violated",
        "violation_type",
        "summary",
    )
    for col in str_cols:
        df[col] = df[col].fillna("").astype(str)

    table = pa.Table.from_pandas(df[[f.name for f in SCHEMA]], schema=SCHEMA, preserve_index=False)
    pq.write_table(table, parquet_path, compression="snappy")
    return parquet_path


def upload_to_s3(parquet_path: Path = _PARQUET_PATH) -> str:
    settings = get_settings()
    s3 = boto3.client("s3", region_name=settings.aws_region)
    s3.upload_file(str(parquet_path), settings.athena_s3_data_bucket, _S3_KEY)
    return f"s3://{settings.athena_s3_data_bucket}/{_S3_KEY}"


def run() -> None:
    console.print("[bold]Converting CSV → Parquet...[/]")
    parquet_path = csv_to_parquet()
    size_kb = parquet_path.stat().st_size // 1024
    console.print(f"  Written to [cyan]{parquet_path}[/] ({size_kb} KB)")

    settings = get_settings()
    if settings.athena_s3_data_bucket:
        console.print(f"[bold]Uploading to S3 bucket:[/] {settings.athena_s3_data_bucket}")
        s3_uri = upload_to_s3(parquet_path)
        console.print(f"  Uploaded to [cyan]{s3_uri}[/]")
    else:
        console.print("[yellow]ATHENA_S3_DATA_BUCKET not set — skipping S3 upload[/]")


if __name__ == "__main__":
    run()
