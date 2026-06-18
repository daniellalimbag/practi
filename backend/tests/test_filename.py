from app.rag import parse_document_filename


def test_parse_announcement_single():
    meta = parse_document_filename("A_20260617")
    assert meta["doc_type"] == "A"
    assert meta["doc_type_label"] == "announcement"
    assert meta["doc_date"] == "2026-06-17"
    assert meta["doc_number"] == "1"


def test_parse_slides_with_number():
    meta = parse_document_filename("S_20260617_02")
    assert meta["doc_type"] == "S"
    assert meta["doc_type_label"] == "slides"
    assert meta["doc_date"] == "2026-06-17"
    assert meta["doc_number"] == "02"


def test_parse_invalid_filename():
    meta = parse_document_filename("readme")
    assert meta["doc_date"] == "unknown"
    assert meta["doc_type"] == "unknown"
