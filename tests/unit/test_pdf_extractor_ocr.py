import sys
import types
from typing import Any

import pytest

from pe_analyst.document_intelligence.extractor import PDFExtractor


class _FakeImageFile:
    def __init__(self, image: Any) -> None:
        self.image = image


class _FakePage:
    def __init__(self, images: list[_FakeImageFile]) -> None:
        self.images = images


@pytest.fixture(autouse=True)
def _clear_pytesseract_module() -> Any:
    original = sys.modules.pop("pytesseract", None)
    yield
    if original is not None:
        sys.modules["pytesseract"] = original
    else:
        sys.modules.pop("pytesseract", None)


def test_ocr_page_uses_pytesseract_when_available() -> None:
    fake_module = types.ModuleType("pytesseract")
    fake_module.image_to_string = lambda image: "Scanned revenue text."  # type: ignore[attr-defined]
    sys.modules["pytesseract"] = fake_module
    page = _FakePage([_FakeImageFile(object())])

    text = PDFExtractor._ocr_page(page)  # type: ignore[arg-type]

    assert text == "Scanned revenue text."


def test_ocr_page_joins_text_from_multiple_images() -> None:
    fake_module = types.ModuleType("pytesseract")
    calls = iter(["First image text.", "Second image text."])
    fake_module.image_to_string = lambda image: next(calls)  # type: ignore[attr-defined]
    sys.modules["pytesseract"] = fake_module
    page = _FakePage([_FakeImageFile(object()), _FakeImageFile(object())])

    text = PDFExtractor._ocr_page(page)  # type: ignore[arg-type]

    assert text == "First image text.\nSecond image text."


def test_ocr_page_returns_empty_string_without_pytesseract_installed() -> None:
    sys.modules["pytesseract"] = None  # type: ignore[assignment]
    page = _FakePage([_FakeImageFile(object())])

    text = PDFExtractor._ocr_page(page)  # type: ignore[arg-type]

    assert text == ""


def test_ocr_page_returns_empty_string_when_tesseract_binary_is_missing() -> None:
    fake_module = types.ModuleType("pytesseract")

    def _raise(image: Any) -> str:
        raise RuntimeError("tesseract is not installed")

    fake_module.image_to_string = _raise  # type: ignore[attr-defined]
    sys.modules["pytesseract"] = fake_module
    page = _FakePage([_FakeImageFile(object())])

    text = PDFExtractor._ocr_page(page)  # type: ignore[arg-type]

    assert text == ""
