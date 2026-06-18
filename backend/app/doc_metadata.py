from pathlib import Path

DOC_TYPE_LABELS = {"A": "announcement", "S": "slides"}


def parse_document_filename(stem: str) -> dict[str, str]:
    """
    Parse filenames:
      <A|S>_<YYYYMMDD>
      <A|S>_<YYYYMMDD>_<Number>
    """
    unknown = {
        "doc_type": "unknown",
        "doc_type_label": "unknown",
        "doc_date": "unknown",
        "doc_number": "1",
    }
    parts = stem.split("_")
    if len(parts) < 2:
        return unknown

    kind = parts[0].upper()
    if kind not in DOC_TYPE_LABELS:
        return unknown

    date_raw = parts[1]
    if len(date_raw) != 8 or not date_raw.isdigit():
        return {**unknown, "doc_type": kind, "doc_type_label": DOC_TYPE_LABELS[kind]}

    doc_date = f"{date_raw[:4]}-{date_raw[4:6]}-{date_raw[6:8]}"
    doc_number = parts[2] if len(parts) > 2 else "1"

    return {
        "doc_type": kind,
        "doc_type_label": DOC_TYPE_LABELS[kind],
        "doc_date": doc_date,
        "doc_number": doc_number,
    }


def source_filename(metadata: dict) -> str:
    return Path(str(metadata.get("source", "unknown"))).name
