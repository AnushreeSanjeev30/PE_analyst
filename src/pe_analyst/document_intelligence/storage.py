"""Filesystem persistence for completed document-intelligence reports."""

from __future__ import annotations

from pathlib import Path

from pe_analyst.core.config import Settings

from .schemas import DocumentIntelligenceReport


class DocumentReportStore:
    """Persists validated reports as JSON so they can be looked up after upload."""

    @staticmethod
    def _path(document_id: str, settings: Settings) -> Path:
        return settings.processed_data_dir / "documents" / f"{document_id}.json"

    @classmethod
    def save(cls, report: DocumentIntelligenceReport, settings: Settings) -> None:
        path = cls._path(report.document_id, settings)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(report.model_dump_json(), encoding="utf-8")

    @classmethod
    def load(cls, document_id: str, settings: Settings) -> DocumentIntelligenceReport | None:
        path = cls._path(document_id, settings)
        if not path.is_file():
            return None
        return DocumentIntelligenceReport.model_validate_json(path.read_text(encoding="utf-8"))

    @classmethod
    def list_all(cls, settings: Settings) -> list[DocumentIntelligenceReport]:
        """Return every stored report, most recently saved first."""

        directory = settings.processed_data_dir / "documents"
        if not directory.is_dir():
            return []
        paths = sorted(
            directory.glob("*.json"), key=lambda path: path.stat().st_mtime, reverse=True
        )
        return [
            DocumentIntelligenceReport.model_validate_json(path.read_text(encoding="utf-8"))
            for path in paths
        ]


__all__ = ["DocumentReportStore"]
