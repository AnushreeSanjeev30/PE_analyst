"""A tiny dependency-free PDF writer for end-to-end tests.

Writes real text (Helvetica) and ruled tables, so the actual extraction stack -- pypdf for text,
pdfplumber for tables -- runs exactly as it does on an uploaded annual report.
"""

from __future__ import annotations

from dataclasses import dataclass, field

PAGE_WIDTH, PAGE_HEIGHT = 612, 792


def _escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


@dataclass
class Page:
    commands: list[str] = field(default_factory=list)
    cursor: float = PAGE_HEIGHT - 60

    def text(self, line: str, *, size: int = 10, x: float = 50) -> Page:
        self.commands.append(f"BT /F1 {size} Tf {x} {self.cursor} Td ({_escape(line)}) Tj ET")
        self.cursor -= size + 6
        return self

    def paragraph(self, lines: list[str]) -> Page:
        for line in lines:
            self.text(line)
        self.cursor -= 8
        return self

    def table(self, rows: list[list[str]], columns: tuple[float, ...] = (50, 330, 440, 550)) -> (
        Page
    ):
        row_height = 18
        top = self.cursor + 4
        for index, row in enumerate(rows):
            baseline = top - (index + 1) * row_height + 5
            for cell, x in zip(row, columns, strict=False):
                self.commands.append(
                    f"BT /F1 9 Tf {x + 4} {baseline} Td ({_escape(cell)}) Tj ET"
                )
        bottom = top - len(rows) * row_height
        for index in range(len(rows) + 1):
            y = top - index * row_height
            self.commands.append(f"{columns[0]} {y} m {columns[-1]} {y} l S")
        for x in columns:
            self.commands.append(f"{x} {top} m {x} {bottom} l S")
        self.cursor = bottom - 20
        return self


def build_pdf(pages: list[Page]) -> bytes:
    objects: list[bytes] = []
    page_ids = [4 + index * 2 for index in range(len(pages))]
    objects.append(b"<< /Type /Catalog /Pages 2 0 R >>")
    kids = " ".join(f"{page_id} 0 R" for page_id in page_ids)
    objects.append(f"<< /Type /Pages /Kids [{kids}] /Count {len(pages)} >>".encode())
    objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
    for page, page_id in zip(pages, page_ids, strict=True):
        objects.append(
            (
                f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {PAGE_WIDTH} {PAGE_HEIGHT}] "
                f"/Resources << /Font << /F1 3 0 R >> >> /Contents {page_id + 1} 0 R >>"
            ).encode()
        )
        stream = "\n".join(page.commands).encode("latin-1")
        objects.append(
            b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream
            + b"\nendstream"
        )

    output = bytearray(b"%PDF-1.4\n")
    offsets = []
    for number, body in enumerate(objects, start=1):
        offsets.append(len(output))
        output += f"{number} 0 obj\n".encode() + body + b"\nendobj\n"
    xref = len(output)
    output += f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode()
    output += b"".join(f"{offset:010d} 00000 n \n".encode() for offset in offsets)
    output += (
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n"
    ).encode()
    return bytes(output)
