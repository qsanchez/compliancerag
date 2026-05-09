import json
from dataclasses import dataclass, field

import psycopg
import structlog

from config import get_settings

logger = structlog.get_logger()

_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS audit_log (
    id              BIGSERIAL PRIMARY KEY,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    question        TEXT NOT NULL,
    route           VARCHAR(20),
    answer          TEXT,
    citations       JSONB NOT NULL DEFAULT '[]',
    has_chart       BOOLEAN NOT NULL DEFAULT FALSE,
    model_version   VARCHAR(100),
    latency_ms      FLOAT,
    injection_blocked BOOLEAN NOT NULL DEFAULT FALSE
)
"""


@dataclass
class AuditRecord:
    question: str
    route: str | None = None
    answer: str | None = None
    citations: list[str] = field(default_factory=list)
    has_chart: bool = False
    model_version: str | None = None
    latency_ms: float | None = None
    injection_blocked: bool = False


def log_query(record: AuditRecord) -> None:
    settings = get_settings()
    if not settings.database_url:
        return

    try:
        with psycopg.connect(settings.database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(_CREATE_TABLE)
                cur.execute(
                    """
                    INSERT INTO audit_log
                        (question, route, answer, citations, has_chart,
                         model_version, latency_ms, injection_blocked)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        record.question,
                        record.route,
                        record.answer,
                        json.dumps(record.citations),
                        record.has_chart,
                        record.model_version,
                        record.latency_ms,
                        record.injection_blocked,
                    ),
                )
            conn.commit()
    except Exception:
        logger.warning("audit_log_failed", question=record.question[:80])
