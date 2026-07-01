import sqlite3
import tempfile
from pathlib import Path
from unittest.mock import patch

from app.audit import init_audit_db, list_recent_logs, log_chat_error, log_chat_success


def test_init_audit_db_creates_table():
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        db_path = Path(tmp) / "audit.db"
        with patch.object(__import__("app.audit", fromlist=["settings"]).settings, "ENABLE_AUDIT_LOGGING", True):
            init_audit_db(db_path)

        conn = sqlite3.connect(db_path)
        tables = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        conn.close()

        assert "chat_audit" in tables


def test_log_chat_success_and_list_recent():
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        db_path = Path(tmp) / "audit.db"
        audit_settings = __import__("app.audit", fromlist=["settings"]).settings
        with patch.object(audit_settings, "ENABLE_AUDIT_LOGGING", True), patch.object(
            audit_settings, "AUDIT_DB_PATH", db_path
        ):
            init_audit_db(db_path)
            row_id = log_chat_success(
                message="Where do I upload reports?",
                history=[{"role": "user", "content": "hello"}],
                answer="Upload them to Canvas.",
                sources=[{"source": "A_20250310.docx", "excerpt": "Canvas upload"}],
                query_date="2026-06-30",
                llm_provider="groq",
                model="llama-3.1-8b-instant",
            )
            logs = list_recent_logs(limit=10, db_path=db_path)

        assert row_id is not None
        assert len(logs) == 1
        assert logs[0]["message"] == "Where do I upload reports?"
        assert logs[0]["answer"] == "Upload them to Canvas."
        assert logs[0]["status"] == "success"
        assert logs[0]["sources"][0]["source"] == "A_20250310.docx"


def test_log_chat_error():
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        db_path = Path(tmp) / "audit.db"
        audit_settings = __import__("app.audit", fromlist=["settings"]).settings
        with patch.object(audit_settings, "ENABLE_AUDIT_LOGGING", True), patch.object(
            audit_settings, "AUDIT_DB_PATH", db_path
        ):
            init_audit_db(db_path)
            row_id = log_chat_error(
                message="hello",
                history=[],
                error="Vector store not initialized",
            )
            logs = list_recent_logs(db_path=db_path)

        assert row_id is not None
        assert logs[0]["status"] == "error"
        assert logs[0]["error"] == "Vector store not initialized"
        assert logs[0]["answer"] is None


def test_logging_disabled_returns_none():
    audit_settings = __import__("app.audit", fromlist=["settings"]).settings
    with patch.object(audit_settings, "ENABLE_AUDIT_LOGGING", False):
        row_id = log_chat_success(
            message="test",
            history=[],
            answer="answer",
            sources=[],
            query_date="2026-06-30",
            llm_provider="groq",
            model="test",
        )
        assert row_id is None
