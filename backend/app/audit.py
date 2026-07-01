"""SQLite audit logging for chat requests."""

from __future__ import annotations

import json
import logging
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from app.config import settings

logger = logging.getLogger(__name__)

_CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS chat_audit (
    id TEXT PRIMARY KEY,
    created_at TEXT NOT NULL,
    message TEXT NOT NULL,
    history_json TEXT NOT NULL,
    answer TEXT,
    sources_json TEXT,
    query_date TEXT,
    llm_provider TEXT,
    model TEXT,
    status TEXT NOT NULL,
    error TEXT
);
"""

_CREATE_INDEX_SQL = """
CREATE INDEX IF NOT EXISTS idx_chat_audit_created_at
ON chat_audit (created_at DESC);
"""


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@contextmanager
def _db(db_path: Path | None = None) -> Iterator[sqlite3.Connection]:
    path = db_path or settings.AUDIT_DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_audit_db(db_path: Path | None = None) -> None:
    """Create audit tables if they do not exist."""
    if not settings.ENABLE_AUDIT_LOGGING:
        return

    with _db(db_path) as conn:
        conn.execute(_CREATE_TABLE_SQL)
        conn.execute(_CREATE_INDEX_SQL)
    logger.info("Audit DB ready at %s", db_path or settings.AUDIT_DB_PATH)


def _insert_row(
    *,
    message: str,
    history: list[dict[str, Any]],
    status: str,
    answer: str | None = None,
    sources: list[dict[str, Any]] | None = None,
    query_date: str | None = None,
    llm_provider: str | None = None,
    model: str | None = None,
    error: str | None = None,
    db_path: Path | None = None,
) -> str | None:
    if not settings.ENABLE_AUDIT_LOGGING:
        return None

    row_id = str(uuid.uuid4())
    try:
        with _db(db_path) as conn:
            conn.execute(
                """
                INSERT INTO chat_audit (
                    id, created_at, message, history_json, answer, sources_json,
                    query_date, llm_provider, model, status, error
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    row_id,
                    _utc_now_iso(),
                    message,
                    json.dumps(history, ensure_ascii=False),
                    answer,
                    json.dumps(sources or [], ensure_ascii=False),
                    query_date,
                    llm_provider,
                    model,
                    status,
                    error,
                ),
            )
        return row_id
    except Exception as exc:
        logger.warning("Failed to write audit log: %s", exc)
        return None


def log_chat_success(
    *,
    message: str,
    history: list[dict[str, Any]],
    answer: str,
    sources: list[dict[str, Any]],
    query_date: str,
    llm_provider: str,
    model: str,
) -> str | None:
    return _insert_row(
        message=message,
        history=history,
        status="success",
        answer=answer,
        sources=sources,
        query_date=query_date,
        llm_provider=llm_provider,
        model=model,
    )


def log_chat_error(
    *,
    message: str,
    history: list[dict[str, Any]],
    error: str,
    query_date: str | None = None,
    llm_provider: str | None = None,
    model: str | None = None,
) -> str | None:
    return _insert_row(
        message=message,
        history=history,
        status="error",
        query_date=query_date,
        llm_provider=llm_provider,
        model=model,
        error=error,
    )


def list_recent_logs(limit: int = 50, db_path: Path | None = None) -> list[dict[str, Any]]:
    """Return recent audit rows, newest first."""
    if not settings.ENABLE_AUDIT_LOGGING:
        return []

    safe_limit = max(1, min(limit, 500))
    with _db(db_path) as conn:
        rows = conn.execute(
            """
            SELECT id, created_at, message, history_json, answer, sources_json,
                   query_date, llm_provider, model, status, error
            FROM chat_audit
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (safe_limit,),
        ).fetchall()

    results: list[dict[str, Any]] = []
    for row in rows:
        results.append(
            {
                "id": row["id"],
                "created_at": row["created_at"],
                "message": row["message"],
                "history": json.loads(row["history_json"] or "[]"),
                "answer": row["answer"],
                "sources": json.loads(row["sources_json"] or "[]"),
                "query_date": row["query_date"],
                "llm_provider": row["llm_provider"],
                "model": row["model"],
                "status": row["status"],
                "error": row["error"],
            }
        )
    return results
