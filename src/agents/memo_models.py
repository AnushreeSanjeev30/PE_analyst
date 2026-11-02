"""Typed output contract for the Investment Memo Agent."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class MemoSection:
    heading: str
    body: str
    bullets: list[str] = field(default_factory=list)


@dataclass(slots=True)
class InvestmentMemo:
    company_name: str
    recommendation: str
    sections: list[MemoSection] = field(default_factory=list)
    # LLM-written draft over the same facts; None when no narrator is configured or it failed.
    llm_draft: str | None = None
    llm_warnings: list[str] = field(default_factory=list)
    markdown: str = ""

    def render_markdown(self) -> str:
        lines = [f"# Investment Memo: {self.company_name}", "",
                 f"**Recommendation:** {self.recommendation}", ""]
        for section in self.sections:
            lines += [f"## {section.heading}", "", section.body, ""]
            lines += [f"- {bullet}" for bullet in section.bullets]
            if section.bullets:
                lines.append("")
        return "\n".join(lines).rstrip() + "\n"
