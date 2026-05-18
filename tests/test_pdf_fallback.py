"""
Tests for the pdf2image fallback path in load_pdf_images.

When pypdfium2 raises PdfiumError (e.g. for XFA-based fillable forms such as
ACORD insurance forms), load_pdf_images must fall back to pdf2image/poppler
and still return a list of PIL images.
"""
from unittest.mock import patch, MagicMock
from PIL import Image

import pytest
import pypdfium2 as pdfium

from chandra.settings import settings


def _make_pil_page(width=800, height=1000, color="white"):
    return Image.new("RGB", (width, height), color=color)


_PDFIUM_FORMAT_ERROR = pdfium.PdfiumError(
    "Failed to load document (PDFium: Data format error)."
)


class TestLoadPdfImagesFallback:
    """load_pdf_images falls back to pdf2image when pdfium raises PdfiumError."""

    def test_fallback_called_on_pdfium_error(self):
        """When pdfium.PdfDocument raises PdfiumError, _load_pdf_images_fallback is used."""
        from chandra.input import load_pdf_images

        fake_pages = [_make_pil_page()]

        with patch("chandra.input.pdfium.PdfDocument", side_effect=_PDFIUM_FORMAT_ERROR), \
             patch("chandra.input._load_pdf_images_fallback", return_value=fake_pages) as mock_fallback:
            result = load_pdf_images("/fake/path.pdf", [])

        mock_fallback.assert_called_once_with(
            "/fake/path.pdf", [], settings.IMAGE_DPI, settings.MIN_PDF_IMAGE_DIM
        )
        assert result == fake_pages

    def test_fallback_returns_images_for_all_pages(self):
        """_load_pdf_images_fallback returns one image per page when no page_range given."""
        from chandra.input import _load_pdf_images_fallback

        fake_pil_pages = [_make_pil_page(color=c) for c in ("white", "lightgrey", "lightyellow")]

        with patch("pdf2image.convert_from_path", return_value=fake_pil_pages):
            result = _load_pdf_images_fallback("/fake/path.pdf", [])

        assert len(result) == 3
        for img in result:
            assert isinstance(img, Image.Image)
            assert img.mode == "RGB"

    def test_fallback_respects_page_range(self):
        """_load_pdf_images_fallback honours page_range filtering."""
        from chandra.input import _load_pdf_images_fallback

        fake_pil_pages = [_make_pil_page() for _ in range(5)]

        with patch("pdf2image.convert_from_path", return_value=fake_pil_pages):
            result = _load_pdf_images_fallback("/fake/path.pdf", [0, 2, 4])

        assert len(result) == 3  # pages 0, 2, 4

    def test_fallback_scales_small_images(self):
        """_load_pdf_images_fallback upscales images whose minimum dimension is too small."""
        from chandra.input import _load_pdf_images_fallback

        tiny_page = Image.new("RGB", (100, 100), "white")

        with patch("pdf2image.convert_from_path", return_value=[tiny_page]):
            result = _load_pdf_images_fallback("/fake/path.pdf", [], min_pdf_image_dim=1000)

        assert len(result) == 1
        assert min(result[0].width, result[0].height) >= 1000

    def test_normal_pdf_still_uses_pdfium(self):
        """load_pdf_images uses pdfium (not the fallback) for normal PDFs."""
        from chandra.input import load_pdf_images

        mock_doc = MagicMock()
        mock_doc.__len__ = MagicMock(return_value=1)
        mock_page = MagicMock()
        mock_page.get_width.return_value = 612
        mock_page.get_height.return_value = 792
        mock_doc.__getitem__ = MagicMock(return_value=mock_page)

        fake_render = MagicMock()
        fake_render.to_pil.return_value = Image.new("RGB", (612, 792), "white")
        mock_page.render.return_value = fake_render

        with patch("chandra.input.pdfium.PdfDocument", return_value=mock_doc), \
             patch("chandra.input._load_pdf_images_fallback") as mock_fallback, \
             patch("chandra.input.flatten"):
            load_pdf_images("/fake/path.pdf", [])

        mock_fallback.assert_not_called()
