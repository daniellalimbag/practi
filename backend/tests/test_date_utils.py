from app.date_utils import resolve_query_date


def test_resolve_query_date_explicit():
    assert resolve_query_date("hello", "2025-04-14") == "2025-04-14"


def test_resolve_query_date_from_iso_in_message():
    assert resolve_query_date("What happened on 2025-04-14?") == "2025-04-14"


def test_resolve_query_date_from_compact_in_message():
    assert resolve_query_date("See announcement 20250414 for details") == "2025-04-14"


def test_resolve_query_date_defaults_to_today():
    from datetime import date

    assert resolve_query_date("hello") == date.today().isoformat()
