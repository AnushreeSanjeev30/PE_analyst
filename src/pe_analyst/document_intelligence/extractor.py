"""Page and table extraction from text-based PDFs."""

from __future__ import annotations

from pathlib import Path

from .models import ExtractedPage, ExtractedPDF, ExtractedTable


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
            pages = [
                ExtractedPage(number + 1, page.extract_text() or "")
                for number, page in enumerate(reader.pages)
            ]
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
                    if rows:
                        result[number] = [ExtractedTable(number, rows)]
        except Exception:
            return {}
        return result
