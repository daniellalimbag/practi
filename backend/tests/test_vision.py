from unittest.mock import patch

from app.image_extract import ExtractedImage, _large_enough
from app.vision import build_vision_appendix, clear_vision_cache, describe_image


def test_large_enough_respects_min_bytes():
    with patch("app.image_extract.settings") as mock_settings:
        mock_settings.VISION_MIN_IMAGE_BYTES = 100
        assert not _large_enough(b"x" * 50)
        assert _large_enough(b"x" * 100)


def test_build_vision_appendix_joins_blocks():
    clear_vision_cache()

    def fake_describe(image_bytes, mime_type, *, context):
        return f"text for {context}"

    images = [
        ExtractedImage("doc.pdf page 1", b"1234567890", "image/png"),
    ]
    appendix = build_vision_appendix(images, describe_fn=fake_describe)
    assert "[Vision extract]" in appendix
    assert "doc.pdf page 1" in appendix
    assert "text for doc.pdf page 1" in appendix


def test_describe_image_skips_when_disabled():
    clear_vision_cache()
    with patch("app.vision.settings") as mock_settings:
        mock_settings.ENABLE_VISION_INGEST = False
        mock_settings.VISION_MIN_IMAGE_BYTES = 1
        assert describe_image(b"abc", "image/png", context="x") == ""
