"""Turns a saved analysis, or a comparison of two, into a Word or PDF file to hand around.

The report on screen is for working; what goes to an investment committee is a document. The
same content is laid out once, as a small format-neutral ``ExportDocument`` (headings,
paragraphs, bullet lists, tables), and then rendered by one of two writers:

* ``render_docx`` -- an editable Word file, because memos get edited before they circulate.
* ``render_pdf``  -- a fixed PDF for sending as-is.

Everything in the document comes from the stored report: the ruling and the reasons for it,
each reason's quoted source with file and page, the memo, the figures, and the assumptions the
run used. Nothing is recalculated here.
"""

from __future__ import annotations

import io
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from xml.sax.saxutils import escape

from .comparison import _METRICS, AnalysisComparison, MetricChange

# ---------------------------------------------------------------------------
# Format-neutral document
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class Heading:
    text: str
    level: int = 1


@dataclass(slots=True)
class Paragraph:
    text: str
    # "normal" | "lead" (the one-line answer) | "note" (small print) | "quote"
    style: str = "normal"


@dataclass(slots=True)
class Bullets:
    items: list[str]


@dataclass(slots=True)
class Table:
    headers: list[str]
    rows: list[list[str]]
    # Relative column widths; equal when omitted.
    widths: list[float] | None = None


Block = Heading | Paragraph | Bullets | Table


@dataclass(slots=True)
class ExportDocument:
    title: str
    subtitle: str
    blocks: list[Block] = field(default_factory=list)
    footer: str = ""


DISCLAIMER = (
    "Prepared with PE-Analyst. Figures are calculated by fixed financial models from the inputs "
    "listed in this document, and quoted passages are extracted automatically from the source "
    "files. Check both against the original documents before relying on them. This is decision "
    "support, not investment advice."
)

# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------


def _dig(data: Any, *path: str) -> Any:
    for key in path:
        if not isinstance(data, dict):
            return None
        data = data.get(key)
    return data


def _pct(value: Any, digits: int = 1) -> str:
    return "-" if not isinstance(value, int | float) else f"{value * 100:.{digits}f}%"


def _num(value: Any, digits: int = 2) -> str:
    return "-" if not isinstance(value, int | float) else f"{value:,.{digits}f}"


def _when(value: Any) -> str:
    if isinstance(value, datetime):
        return value.strftime("%d %b %Y, %H:%M")
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value).strftime("%d %b %Y, %H:%M")
        except ValueError:
            return value
    return "-"


def _metric_text(value: Any, unit: str) -> str:
    if value is None:
        return "-"
    if isinstance(value, str):
        return value
    if unit == "percent":
        return _pct(value)
    if unit == "multiple":
        return f"{value:.2f}x"
    if unit == "money":
        return _num(value)
    # Counts and scores: no decimals when the value is whole ("1", not "1.0").
    return _num(value, 0 if float(value).is_integer() else 1)


def _delta_text(metric: MetricChange) -> str:
    if not metric.changed:
        return "no change"
    if metric.delta is None:
        return "changed"
    sign = "+" if metric.delta > 0 else "-"
    size = abs(metric.delta)
    if metric.unit == "percent":
        return f"{sign}{size * 100:.1f} pts"
    if metric.unit == "multiple":
        return f"{sign}{size:.2f}x"
    return f"{sign}{_num(size)}"


_INPUT_LABELS = {
    "revenue_growth": ("Revenue growth", "percent"),
    "ebit_margin": ("EBIT margin", "percent"),
    "ebitda_margin": ("EBITDA margin", "percent"),
    "tax_rate": ("Tax rate", "percent"),
    "capex_pct_revenue": ("Capex (% of revenue)", "percent"),
    "nwc_pct_revenue": ("Working capital (% of revenue growth)", "percent"),
    "cash": ("Cash", "money"),
    "debt": ("Debt", "money"),
    "shares_outstanding": ("Shares outstanding", "money"),
    "current_price_per_share": ("Current price per share", "money"),
    "entry_multiple": ("Entry multiple (EV / EBITDA)", "multiple"),
    "exit_multiple": ("Exit multiple (EV / EBITDA)", "multiple"),
    "holding_period": ("Holding period (years)", "number"),
}


def input_label(path: str) -> str:
    """A readable name for a dotted request path such as
    ``valuation_assumptions.entry_multiple``."""

    leaf = path.rsplit(".", 1)[-1]
    known = _INPUT_LABELS.get(re.sub(r"\[\d+\]$", "", leaf))
    if known and path.startswith("valuation_assumptions."):
        return known[0]
    peer = re.match(r"valuation_assumptions\.peers\[(\d+)\](?:\.(\w+))?$", path)
    if peer:
        detail = f": {peer.group(2).replace('_', ' ')}" if peer.group(2) else ""
        return f"Comparable company {int(peer.group(1)) + 1}{detail}"
    text = re.sub(r"\[(\d+)\]", lambda match: f" {int(match.group(1)) + 1}", path)
    for prefix in ("valuation_assumptions.", "valuation_inputs."):
        text = text.removeprefix(prefix)
    return text.replace("_", " ").replace(".", ": ").capitalize()


def _input_value(path: str, value: Any) -> str:
    if value is None:
        return "-"
    known = _INPUT_LABELS.get(path.rsplit(".", 1)[-1])
    if known and path.startswith("valuation_assumptions.") and isinstance(value, int | float):
        return _metric_text(value, known[1])
    if isinstance(value, float):
        return _num(value, 4).rstrip("0").rstrip(".")
    return str(value)


# ---------------------------------------------------------------------------
# Building the analysis document
# ---------------------------------------------------------------------------


def _decision_blocks(report: dict[str, Any]) -> list[Block]:
    explanation = _dig(report, "ic_decision", "explanation")
    if not explanation:
        return []
    blocks: list[Block] = [
        Heading("Why this decision"),
        Paragraph(str(explanation.get("headline", "")), "lead"),
    ]
    drivers = explanation.get("drivers") or []
    blocks.append(
        Table(
            ["Area", "Effect", "Weight", "Based on", "Reason"],
            [
                [
                    str(driver.get("area", "")),
                    "Supports" if driver.get("direction") == "Supports" else "Against",
                    _pct(driver.get("weight"), 0),
                    str(driver.get("basis", "")),
                    str(driver.get("statement", "")),
                ]
                for driver in drivers
            ],
            [1.3, 0.9, 0.7, 1.2, 4.4],
        )
    )
    cited = [driver for driver in drivers if driver.get("evidence")]
    if cited:
        blocks.append(Heading("Evidence from the documents", 2))
        for driver in cited:
            blocks.append(Paragraph(str(driver["area"]), "normal"))
            blocks.append(
                Bullets(
                    [
                        f'"{citation["excerpt"]}" - {citation["source"]}, '
                        f"page {citation['page_number']}"
                        for citation in driver["evidence"]
                    ]
                )
            )
    for title, key in (
        ("What would change the ruling", "what_would_change"),
        ("Conditions before signing", "conditions"),
        ("Check before relying on this", "evidence_gaps"),
    ):
        items = explanation.get(key) or []
        if items:
            blocks += [Heading(title, 2), Bullets([str(item) for item in items])]
    return blocks


def _figures_block(report: dict[str, Any]) -> list[Block]:
    rows = []
    for _, label, unit, read in _METRICS:
        value = read(report)
        if value is not None:
            rows.append([label, _metric_text(value, unit)])
    if not rows:
        return []
    return [Heading("Key figures"), Table(["Measure", "Value"], rows, [3.0, 1.5])]


def _scenario_block(report: dict[str, Any]) -> list[Block]:
    cases = _dig(report, "scenario_report", "cases") or []
    if not cases:
        return []
    return [
        Heading("Scenarios", 2),
        Table(
            ["Scenario", "Probability", "Exit multiple", "IRR", "MOIC"],
            [
                [
                    str(case.get("name", "")),
                    _pct(case.get("probability"), 0),
                    f"{case.get('exit_multiple', 0):.1f}x",
                    _pct(case.get("irr")),
                    f"{case.get('moic', 0):.2f}x",
                ]
                for case in cases
            ],
        ),
    ]


def _red_flag_block(report: dict[str, Any]) -> list[Block]:
    flags = _dig(report, "due_diligence_report", "red_flags") or []
    if not flags:
        return []
    return [
        Heading("Red flags", 2),
        Table(
            ["Finding", "Severity", "Source"],
            [
                [
                    str(flag.get("rationale") or flag.get("title", "")),
                    str(flag.get("severity", "")),
                    f"{_dig(flag, 'citation', 'source')}, "
                    f"p. {_dig(flag, 'citation', 'page_number')}",
                ]
                for flag in flags
            ],
            [4.6, 1.0, 2.4],
        ),
    ]


def _memo_blocks(report: dict[str, Any]) -> list[Block]:
    sections = _dig(report, "investment_memo", "sections") or []
    blocks: list[Block] = []
    for section in sections:
        heading = str(section.get("heading", ""))
        # Covered in full, with its sources, by "Why this decision" above.
        if heading == "Decision Rationale and Evidence":
            continue
        blocks.append(Heading(heading, 2))
        if section.get("body"):
            blocks.append(Paragraph(str(section["body"])))
        if section.get("bullets"):
            blocks.append(Bullets([str(item) for item in section["bullets"]]))
    return [Heading("Investment memo"), *blocks] if blocks else []


def _assumption_block(request: dict[str, Any]) -> list[Block]:
    assumptions = request.get("valuation_assumptions")
    if not isinstance(assumptions, dict):
        return []
    rows = [
        [label, _metric_text(assumptions[key], unit)]
        for key, (label, unit) in _INPUT_LABELS.items()
        if assumptions.get(key) is not None
    ]
    blocks: list[Block] = [
        Heading("Assumptions used"),
        Table(["Assumption", "Value"], rows, [3.0, 1.5]),
    ]
    peers = assumptions.get("peers") or []
    if peers:
        blocks += [
            Heading("Comparable companies", 2),
            Table(
                ["Company", "Enterprise value", "Revenue", "EBITDA"],
                [
                    [
                        str(peer.get("name", "")),
                        _num(peer.get("enterprise_value")),
                        _num(peer.get("revenue")),
                        _num(peer.get("ebitda")),
                    ]
                    for peer in peers
                ],
            ),
        ]
    return blocks


def build_analysis_document(analysis: Any) -> ExportDocument:
    """Lay out one saved analysis (a ``DealAnalysisModel`` row) as a committee document."""

    report: dict[str, Any] = analysis.report or {}
    request: dict[str, Any] = analysis.request or {}
    recommendation = analysis.recommendation or report.get("final_recommendation") or "No ruling"
    document = ExportDocument(
        title=f"Investment Committee Memo: {analysis.company_name}",
        subtitle=(
            f"Recommendation: {recommendation}   |   "
            f"Analysis run {_when(analysis.created_at)}"
        ),
        footer=DISCLAIMER,
    )
    if not report:
        document.blocks.append(
            Paragraph(
                analysis.error or "This analysis did not produce a report.", "lead"
            )
        )
        return document
    if report.get("error"):
        document.blocks.append(Paragraph(f"The run did not complete: {report['error']}", "lead"))
    document.blocks += _decision_blocks(report)
    document.blocks += _figures_block(report)
    document.blocks += _scenario_block(report)
    document.blocks += _red_flag_block(report)
    document.blocks += _memo_blocks(report)
    document.blocks += _assumption_block(request)
    return document


# ---------------------------------------------------------------------------
# Building the comparison document
# ---------------------------------------------------------------------------


def build_comparison_document(comparison: AnalysisComparison) -> ExportDocument:
    base, other = comparison.base, comparison.other
    document = ExportDocument(
        title=f"Run Comparison: {other.company_name}",
        subtitle=(
            f"{base.recommendation or 'No ruling'} to {other.recommendation or 'No ruling'}"
            f"   |   Compared {_when(datetime.now())}"
        ),
        footer=DISCLAIMER,
    )
    blocks = document.blocks
    blocks.append(Paragraph(comparison.summary, "lead"))
    blocks.append(
        Table(
            ["", "Company", "Recommendation", "Run on"],
            [
                ["Baseline", base.company_name, base.recommendation or "-", _when(base.created_at)],
                [
                    "Compared with", other.company_name, other.recommendation or "-",
                    _when(other.created_at),
                ],
            ],
            [1.3, 2.4, 1.5, 1.8],
        )
    )

    blocks.append(Heading("What changed in the inputs"))
    if comparison.input_changes:
        blocks.append(
            Table(
                ["Input", "Baseline", "Compared with"],
                [
                    [
                        input_label(change.path),
                        _input_value(change.path, change.base),
                        _input_value(change.path, change.other),
                    ]
                    for change in comparison.input_changes
                ],
                [3.4, 1.8, 1.8],
            )
        )
        if comparison.input_changes_truncated:
            blocks.append(Paragraph("More inputs differ than are listed here.", "note"))
    else:
        blocks.append(Paragraph("The two runs used identical inputs."))

    blocks.append(Heading("What changed in the results"))
    blocks.append(
        Table(
            ["Result", "Baseline", "Compared with", "Change"],
            [
                [
                    metric.label,
                    _metric_text(metric.base, metric.unit),
                    _metric_text(metric.other, metric.unit),
                    _delta_text(metric),
                ]
                for metric in comparison.metrics
            ],
            [3.0, 1.4, 1.4, 1.2],
        )
    )

    flipped = [driver for driver in comparison.drivers if driver.changed]
    blocks.append(Heading("Scorecard votes that flipped"))
    if not flipped:
        blocks.append(Paragraph("No scorecard area changed its vote."))
    for driver in flipped:
        blocks.append(
            Paragraph(f"{driver.area}: {driver.base_direction} to {driver.other_direction}")
        )
        blocks.append(
            Bullets(
                [
                    f"Baseline: {driver.base_statement or '-'}",
                    f"Compared with: {driver.other_statement or '-'}",
                ]
            )
        )
    return document


# ---------------------------------------------------------------------------
# Word
# ---------------------------------------------------------------------------

DOCX_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
PDF_MEDIA_TYPE = "application/pdf"


def render_docx(document: ExportDocument) -> bytes:
    from docx import Document
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.shared import Pt, RGBColor

    output = Document()
    normal = output.styles["Normal"]
    normal.font.name = "Calibri"
    normal.font.size = Pt(10.5)

    output.add_heading(document.title, level=0)
    subtitle = output.add_paragraph(document.subtitle)
    subtitle.runs[0].font.size = Pt(11)
    subtitle.runs[0].font.color.rgb = RGBColor(0x55, 0x55, 0x55)

    for block in document.blocks:
        if isinstance(block, Heading):
            output.add_heading(block.text, level=block.level)
        elif isinstance(block, Paragraph):
            paragraph = output.add_paragraph()
            run = paragraph.add_run(block.text)
            if block.style == "lead":
                run.bold = True
                run.font.size = Pt(12)
            elif block.style == "note":
                run.italic = True
                run.font.size = Pt(9)
            elif block.style == "quote":
                run.italic = True
        elif isinstance(block, Bullets):
            for item in block.items:
                output.add_paragraph(item, style="List Bullet")
        elif isinstance(block, Table):
            table = output.add_table(rows=1, cols=len(block.headers))
            table.style = "Light Grid Accent 1"
            for cell, header in zip(table.rows[0].cells, block.headers, strict=True):
                cell.text = header
                for run in cell.paragraphs[0].runs:
                    run.bold = True
            for row in block.rows:
                cells = table.add_row().cells
                for cell, value in zip(cells, row, strict=False):
                    cell.text = value
            output.add_paragraph()

    if document.footer:
        footer = output.add_paragraph()
        footer.alignment = WD_ALIGN_PARAGRAPH.LEFT
        run = footer.add_run(document.footer)
        run.italic = True
        run.font.size = Pt(8.5)
        run.font.color.rgb = RGBColor(0x66, 0x66, 0x66)

    buffer = io.BytesIO()
    output.save(buffer)
    return buffer.getvalue()


# ---------------------------------------------------------------------------
# PDF
# ---------------------------------------------------------------------------

# The built-in PDF fonts cover Windows-1252 only. Swap the few symbols that fall outside it
# for plain equivalents instead of letting them print as black boxes.
_PDF_REPLACEMENTS = {
    "→": "->", "←": "<-", "−": "-", "≥": ">=", "≤": "<=",
    "≈": "~", "×": "x", " ": " ", "‑": "-", " ": " ",
}


def _pdf_text(text: str) -> str:
    for symbol, plain in _PDF_REPLACEMENTS.items():
        text = text.replace(symbol, plain)
    safe = text.encode("cp1252", "replace").decode("cp1252")
    return escape(safe)


def render_pdf(document: ExportDocument) -> bytes:
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_LEFT
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import ListFlowable, ListItem, SimpleDocTemplate, Spacer
    from reportlab.platypus import Paragraph as PdfParagraph
    from reportlab.platypus import Table as PdfTable

    base = getSampleStyleSheet()
    ink = colors.HexColor("#1f2933")
    muted = colors.HexColor("#5b6670")
    accent = colors.HexColor("#256abf")
    styles = {
        "title": ParagraphStyle("title", parent=base["Title"], fontSize=18, leading=22,
                                alignment=TA_LEFT, textColor=ink, spaceAfter=4),
        "subtitle": ParagraphStyle("subtitle", parent=base["Normal"], fontSize=10.5,
                                   textColor=muted, spaceAfter=10),
        "h1": ParagraphStyle("h1", parent=base["Heading2"], fontSize=13, leading=16,
                             textColor=accent, spaceBefore=12, spaceAfter=5),
        "h2": ParagraphStyle("h2", parent=base["Heading3"], fontSize=11, leading=14,
                             textColor=ink, spaceBefore=8, spaceAfter=3),
        "normal": ParagraphStyle("normal", parent=base["Normal"], fontSize=9.5, leading=13,
                                 textColor=ink, spaceAfter=4),
        "lead": ParagraphStyle("lead", parent=base["Normal"], fontName="Helvetica-Bold",
                               fontSize=10.5, leading=14, textColor=ink, spaceAfter=6),
        "note": ParagraphStyle("note", parent=base["Normal"], fontName="Helvetica-Oblique",
                               fontSize=8, leading=10.5, textColor=muted, spaceAfter=4),
        "cell": ParagraphStyle("cell", parent=base["Normal"], fontSize=8.5, leading=11,
                               textColor=ink),
        "head": ParagraphStyle("head", parent=base["Normal"], fontName="Helvetica-Bold",
                               fontSize=8.5, leading=11, textColor=colors.white),
    }
    styles["quote"] = ParagraphStyle("quote", parent=styles["normal"],
                                     fontName="Helvetica-Oblique")

    page_width = A4[0] - 36 * mm
    story: list[Any] = [
        PdfParagraph(_pdf_text(document.title), styles["title"]),
        PdfParagraph(_pdf_text(document.subtitle), styles["subtitle"]),
    ]
    if document.footer:
        # Up front rather than at the end: a trailing note can be pushed onto a page of its
        # own, and a reader should see the caveat before the figures in any case.
        story.append(PdfParagraph(_pdf_text(document.footer), styles["note"]))
    for block in document.blocks:
        if isinstance(block, Heading):
            story.append(
                PdfParagraph(_pdf_text(block.text), styles["h1" if block.level <= 1 else "h2"])
            )
        elif isinstance(block, Paragraph):
            story.append(PdfParagraph(_pdf_text(block.text), styles[block.style]))
        elif isinstance(block, Bullets):
            story.append(
                ListFlowable(
                    [
                        ListItem(PdfParagraph(_pdf_text(item), styles["normal"]), leftIndent=12)
                        for item in block.items
                    ],
                    bulletType="bullet",
                    start="•",
                    leftIndent=12,
                )
            )
            story.append(Spacer(1, 3))
        elif isinstance(block, Table):
            widths = block.widths or [1.0] * len(block.headers)
            total = sum(widths)
            data = [[PdfParagraph(_pdf_text(text), styles["head"]) for text in block.headers]]
            data += [
                [PdfParagraph(_pdf_text(text), styles["cell"]) for text in row]
                for row in block.rows
            ]
            table = PdfTable(
                data, colWidths=[page_width * width / total for width in widths], repeatRows=1
            )
            table.setStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), accent),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#c9d1d9")),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1),
                     [colors.white, colors.HexColor("#f5f7fa")]),
                    ("LEFTPADDING", (0, 0), (-1, -1), 5),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ]
            )
            story += [table, Spacer(1, 8)]
    def number_pages(canvas: Any, _: Any) -> None:
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(muted)
        canvas.drawRightString(A4[0] - 18 * mm, 10 * mm, f"Page {canvas.getPageNumber()}")
        canvas.drawString(18 * mm, 10 * mm, document.title[:90].encode("cp1252", "replace")
                          .decode("cp1252"))
        canvas.restoreState()

    buffer = io.BytesIO()
    SimpleDocTemplate(
        buffer, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm,
        topMargin=16 * mm, bottomMargin=18 * mm, title=document.title, author="PE-Analyst",
    ).build(story, onFirstPage=number_pages, onLaterPages=number_pages)
    return buffer.getvalue()


def render(document: ExportDocument, file_format: str) -> tuple[bytes, str, str]:
    """Render to ``pdf`` or ``docx``. Returns the bytes, the media type and the extension."""

    if file_format == "docx":
        return render_docx(document), DOCX_MEDIA_TYPE, "docx"
    if file_format == "pdf":
        return render_pdf(document), PDF_MEDIA_TYPE, "pdf"
    raise ValueError("format must be 'pdf' or 'docx'")


def safe_filename(text: str) -> str:
    """A download-safe file stem: letters, digits, dashes and underscores only."""

    return re.sub(r"[^A-Za-z0-9]+", "_", text).strip("_")[:80] or "report"


__all__ = [
    "DISCLAIMER",
    "ExportDocument",
    "build_analysis_document",
    "build_comparison_document",
    "input_label",
    "render",
    "render_docx",
    "render_pdf",
    "safe_filename",
]
