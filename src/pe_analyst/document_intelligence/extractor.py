"""Page and table extraction from text-based PDFs."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from .models import ExtractedPage, ExtractedPDF, ExtractedTable

if TYPE_CHECKING:
    from pypdf._page import PageObject


_TEXT_TABLE_SETTINGS = {"vertical_strategy": "text", "horizontal_strategy": "text"}


class PDFExtractionError(RuntimeError):
    """Raised when PDF source extraction cannot be completed."""


class PDFExtractor:
    def extract(self, path: Path) -> ExtractedPDF:
        if path.suffix.lower() != ".pdf":
            raise ValueError("Document intelligence accepts PDF files only")
        if not path.is_file():
            raise FileNotFoundError(path)
        try:
            from pypdf import PdfReader
        except ImportError as error:
            raise PDFExtractionError(
                "pypdf is required; install the project PDF dependencies"
            ) from error
        try:
            reader = PdfReader(str(path))
            pages = []
            for number, page in enumerate(reader.pages):
                text = page.extract_text() or ""
                if not text.strip():
                    text = self._ocr_page(page)
                pages.append(ExtractedPage(number + 1, text))
        except Exception as error:
            raise PDFExtractionError(f"Unable to read PDF: {error}") from error
        tables = self._extract_tables(path)
        pages_with_tables = [
            ExtractedPage(page.page_number, page.text, tables.get(page.page_number, []))
            for page in pages
        ]
        metadata = {
            str(key): str(value)
            for key, value in (reader.metadata or {}).items()
            if value is not None
        }
        return ExtractedPDF(path, len(pages_with_tables), pages_with_tables, metadata)

    @staticmethod
    def _ocr_page(page: PageObject) -> str:
        """Best-effort OCR fallback for a page with no extractable text (a scanned page).

        Needs both the ``pytesseract`` package (a pip dependency) and the Tesseract OCR
        binary on the host (not pip-installable). If either is missing, or OCR otherwise
        fails, this returns an empty string -- the caller's existing "OCR is required"
        warning still fires exactly as it did before OCR support existed.
        """

        try:
            import pytesseract  # type: ignore[import-untyped]
        except ImportError:
            return ""
        try:
            texts = [pytesseract.image_to_string(image_file.image) for image_file in page.images]
        except Exception:
            return ""
        return "\n".join(text for text in texts if text.strip())

    @staticmethod
    def _extract_tables(path: Path) -> dict[int, list[ExtractedTable]]:
        try:
            import pdfplumber
        except ImportError:
            return {}
        result: dict[int, list[ExtractedTable]] = {}
        try:
            with pdfplumber.open(path) as pdf:
                for number, page in enumerate(pdf.pages, start=1):
                    rows = [row for table in page.extract_tables() for row in table if row]
                    if not rows:
                        # Most filings draw statements without ruling lines; fall back to
                        # whitespace-aligned columns. Only statement pages consume these rows.
                        rows = [
                            row
                            for table in page.extract_tables(_TEXT_TABLE_SETTINGS)
                            for row in table
                            if row
                        ]
                    if rows:
                        result[number] = [ExtractedTable(number, rows)]
        except Exception:
            return {}
        return result
