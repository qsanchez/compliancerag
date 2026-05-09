import re
from pathlib import Path
from typing import Any

import litellm
from langsmith import traceable
from pyathena import connect

from config import get_settings

_PROMPTS_DIR = Path(__file__).parent.parent / "prompts"


def _load_prompt(name: str) -> str:
    return (_PROMPTS_DIR / name).read_text(encoding="utf-8")


def _generate_sql(question: str) -> str:
    settings = get_settings()
    system = _load_prompt("sql_system.txt").format(database=settings.athena_database)
    response = litellm.completion(
        model=settings.litellm_model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": question},
        ],
        temperature=0.0,
    )
    return (response.choices[0].message.content or "").strip()


def _validate_sql(sql: str) -> None:
    normalized = sql.upper().lstrip()
    for keyword in ("INSERT", "UPDATE", "DELETE", "DROP", "CREATE", "ALTER", "TRUNCATE"):
        if re.search(rf"\b{keyword}\b", normalized):
            raise ValueError(f"Forbidden keyword '{keyword}' in generated SQL")
    if not normalized.startswith("SELECT"):
        raise ValueError(f"Only SELECT queries are allowed. Got: {sql[:120]}")


def _run_query(sql: str) -> list[dict[str, Any]]:
    settings = get_settings()
    conn = connect(
        s3_staging_dir=settings.athena_s3_output,
        region_name=settings.aws_region,
        schema_name=settings.athena_database,
    )
    cursor = conn.cursor()
    cursor.execute(sql)
    columns = [desc[0] for desc in (cursor.description or [])]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]


def _summarise(question: str, rows: list[dict]) -> str:
    if not rows:
        return "No data found for this query."
    settings = get_settings()
    context = "\n".join(str(r) for r in rows[:20])
    response = litellm.completion(
        model=settings.litellm_model,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a compliance analytics assistant. Summarise the query results "
                    "in 2-3 concise sentences answering the user's question. Include key numbers."
                ),
            },
            {"role": "user", "content": f"Question: {question}\n\nData:\n{context}"},
        ],
    )
    return response.choices[0].message.content or ""


@traceable(name="query_metrics", run_type="tool")
def query_metrics(question: str) -> dict:
    sql = _generate_sql(question)
    _validate_sql(sql)
    rows = _run_query(sql)
    summary = _summarise(question, rows)
    return {"summary": summary, "rows": rows, "sql": sql}
