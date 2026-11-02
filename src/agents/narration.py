"""LLM narration layered on top of the deterministic agents.

The control principle is unchanged: every number, score and recommendation still comes from the
deterministic engines. A :class:`Narrator` only turns an agent's finished report into analyst
prose. It never raises (a missing key, rate limit or malformed reply degrades to "no narrative"
plus a warning), and it flags any number in the prose that does not appear in the facts it was
given, so hallucinated figures are visible instead of silent.

Every call is appended to a JSONL log in chat fine-tuning format (system / user / assistant
messages plus metadata). Reviewing and correcting that log is how a fine-tuning dataset is built.
"""

from __future__ import annotations

import json
import math
import re
from dataclasses import asdict, dataclass, field, is_dataclass
from datetime import UTC, date, datetime
from enum import Enum
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from pe_analyst.core.config import Settings
from pe_analyst.llm.factory import build_llm_service, select_provider
from pe_analyst.llm.models import LLMMessage, LLMProviderName, LLMRequest
from pe_analyst.llm.service import LLMService

from .prompts import NARRATION_PROMPT, SYSTEM_PROMPT

_MAX_LIST_ITEMS = 15
_MAX_STRING_CHARS = 400
_NUMBER = re.compile(r"(?<![\w.])-?\$?\d[\d,]*(?:\.\d+)?\s*(?:%|x|bn|billion|m|million|k)?", re.I)

@dataclass(slots=True)
class Narrative:
    agent: str
    commentary: str
    key_points: list[str] = field(default_factory=list)
    provider: str | None = None
    model: str | None = None
    ungrounded_numbers: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return bool(self.commentary)


def to_jsonable(value: Any, *, truncate: bool = True) -> Any:
    """Dataclasses/enums/UUIDs -> plain JSON, trimmed so prompts stay small."""

    if is_dataclass(value) and not isinstance(value, type):
        value = asdict(value)
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, UUID | datetime | date | Path):
        return str(value)
    if isinstance(value, float):
        return None if math.isnan(value) or math.isinf(value) else round(value, 4)
    if isinstance(value, str):
        return value[:_MAX_STRING_CHARS] if truncate else value
    if isinstance(value, dict):
        return {str(key): to_jsonable(item, truncate=truncate) for key, item in value.items()}
    if isinstance(value, list | tuple | set):
        items = list(value)[:_MAX_LIST_ITEMS] if truncate else list(value)
        return [to_jsonable(item, truncate=truncate) for item in items]
    return value


def _fact_numbers(facts: Any) -> list[float]:
    numbers: list[float] = []

    def walk(node: Any) -> None:
        if isinstance(node, bool):
            return
        if isinstance(node, int | float):
            numbers.append(float(node))
        elif isinstance(node, str):
            numbers.extend(value for value in map(_parse_number, _NUMBER.findall(node)) if value)
        elif isinstance(node, dict):
            for item in node.values():
                walk(item)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(facts)
    return numbers


def _parse_number(token: str) -> float | None:
    text = token.strip().lower().replace("$", "").replace(",", "")
    scale = 1.0
    for suffix, factor in (("billion", 1e9), ("bn", 1e9), ("million", 1e6), ("m", 1e6),
                           ("k", 1e3), ("%", 1.0), ("x", 1.0)):
        if text.endswith(suffix):
            text, scale = text[: -len(suffix)].strip(), factor
            break
    try:
        return float(text) * scale
    except ValueError:
        return None


def find_ungrounded_numbers(text: str, facts: Any) -> list[str]:
    """Numbers in ``text`` that match no fact (allowing % <-> decimal and unit rescaling).

    Small integers and calendar years are ignored -- "three risks", "a 5-year hold" and "2025"
    are not claims worth flagging.
    """

    known = _fact_numbers(facts)
    flagged: list[str] = []
    for token in _NUMBER.findall(text):
        value = _parse_number(token)
        if value is None or (value.is_integer() and (abs(value) <= 10 or 1900 <= value <= 2100)):
            continue
        candidates = {value, value / 100, value * 100, value / 1e3, value / 1e6, value / 1e9}
        if not any(
            math.isclose(candidate, fact, rel_tol=0.015, abs_tol=0.005)
            for candidate in candidates
            for fact in known
        ):
            flagged.append(token.strip())
    return flagged


class NarrationLog:
    """Append-only JSONL log of every narration call, in chat fine-tuning format."""

    def __init__(self, directory: Path) -> None:
        self.path = directory / f"narration_{datetime.now(UTC):%Y%m%d}.jsonl"

    def append(self, record: dict[str, Any]) -> None:
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(record, ensure_ascii=False) + "\n")
        except OSError:
            pass  # logging must never break an underwriting run


class Narrator:
    def __init__(
        self,
        llm_service: LLMService,
        provider: LLMProviderName,
        model: str,
        *,
        log: NarrationLog | None = None,
        temperature: float = 0.2,
    ) -> None:
        self.llm_service = llm_service
        self.provider = provider
        self.model = model
        self.log = log
        self.temperature = temperature

    def narrate(
        self,
        agent: str,
        instructions: str,
        facts: dict[str, Any],
        *,
        max_output_tokens: int = 900,
    ) -> Narrative:
        facts_json = json.dumps(to_jsonable(facts), ensure_ascii=False, indent=1)
        user_prompt = NARRATION_PROMPT.substitute(
            agent=agent, instructions=instructions.strip(), facts=facts_json
        )
        request = LLMRequest(
            messages=[LLMMessage("user", user_prompt)],
            model=self.model,
            temperature=self.temperature,
            max_output_tokens=max_output_tokens,
            system_prompt=SYSTEM_PROMPT,
            response_schema={"type": "object"},
        )
        raw_text = ""
        try:
            raw_text = self.llm_service.generate(self.provider, request).text
            narrative = self._parse(agent, raw_text)
            narrative.ungrounded_numbers = find_ungrounded_numbers(
                " ".join([narrative.commentary, *narrative.key_points]), facts
            )
            if narrative.ungrounded_numbers:
                narrative.warnings.append(
                    "Narrative cites figures not present in the agent's output: "
                    + ", ".join(narrative.ungrounded_numbers)
                )
        except Exception as error:  # noqa: BLE001 - narration is optional, never fatal
            narrative = Narrative(agent, "", warnings=[f"Narration failed: {error}"])
        narrative.provider, narrative.model = self.provider.value, self.model
        self._log(agent, user_prompt, raw_text, narrative)
        return narrative

    @staticmethod
    def _parse(agent: str, text: str) -> Narrative:
        cleaned = text.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?|```$", "", cleaned, flags=re.M).strip()
        try:
            body = json.loads(cleaned)
        except json.JSONDecodeError:
            return Narrative(agent, cleaned, warnings=["Model did not return JSON; kept raw text."])
        if not isinstance(body, dict):
            return Narrative(agent, cleaned, warnings=["Model returned non-object JSON."])
        points = body.get("key_points") or []
        return Narrative(
            agent,
            str(body.get("commentary", "")).strip(),
            [str(point) for point in points] if isinstance(points, list) else [],
        )

    def _log(self, agent: str, user_prompt: str, raw_text: str, narrative: Narrative) -> None:
        if self.log is None:
            return
        self.log.append(
            {
                "id": str(uuid4()),
                "timestamp": datetime.now(UTC).isoformat(),
                "agent": agent,
                "provider": self.provider.value,
                "model": self.model,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                    {"role": "assistant", "content": raw_text},
                ],
                "ungrounded_numbers": narrative.ungrounded_numbers,
                "warnings": narrative.warnings,
                # Reviewers set this to "approved" / "rejected" (or rewrite the assistant turn)
                # before the record is used for fine-tuning; see scripts/export_finetune_data.py.
                "review": None,
            }
        )


def build_narrator(settings: Settings) -> Narrator | None:
    """The configured narrator, or None when the chosen provider has no credentials."""

    service = build_llm_service(settings)
    selected = select_provider(settings, service)
    if selected is None:
        return None
    provider, model = selected
    log = NarrationLog(settings.llm_log_dir) if settings.llm_log_dir else None
    return Narrator(service, provider, model, log=log)


__all__ = [
    "NarrationLog",
    "Narrative",
    "Narrator",
    "build_narrator",
    "find_ungrounded_numbers",
    "to_jsonable",
]
