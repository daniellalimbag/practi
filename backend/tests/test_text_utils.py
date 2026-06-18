from app.text_utils import normalize_extracted_text


def test_normalize_spaced_slide_line():
    raw = "P r a c t i c u m O r i e n t a t i o n"
    assert "Practicum" in normalize_extracted_text(raw)


def test_normalize_keeps_normal_line():
    raw = "This is a normal sentence about internships."
    assert normalize_extracted_text(raw) == raw
