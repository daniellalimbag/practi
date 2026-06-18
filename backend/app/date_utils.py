import re
from datetime import date, datetime

DATE_ISO_RE = re.compile(r"\b(\d{4})-(\d{2})-(\d{2})\b")
DATE_COMPACT_RE = re.compile(r"\b(20\d{6})\b")


def today_iso() -> str:
    return date.today().isoformat()


def _validate_iso(value: str) -> str | None:
    try:
        datetime.strptime(value, "%Y-%m-%d")
        return value
    except ValueError:
        return None


def _compact_to_iso(value: str) -> str | None:
    if len(value) != 8 or not value.isdigit():
        return None
    return _validate_iso(f"{value[:4]}-{value[4:6]}-{value[6:8]}")


def resolve_query_date(message: str, explicit: str | None = None) -> str:
    """
    Determine the reference date for retrieval.
    Priority: explicit API field > date in message > today.
    """
    if explicit:
        validated = _validate_iso(explicit.strip())
        if validated:
            return validated

    match = DATE_ISO_RE.search(message)
    if match:
        validated = _validate_iso(match.group(0))
        if validated:
            return validated

    for match in DATE_COMPACT_RE.finditer(message):
        validated = _compact_to_iso(match.group(1))
        if validated:
            return validated

    return today_iso()
