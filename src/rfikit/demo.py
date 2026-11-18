from typing import Any

from rfikit.cite import extract
from rfikit.synth import generate

MAX_CHARS = 200_000
SAMPLE_RFIS = 3


def utf16_offsets(text: str) -> list[int]:
    found = [0]
    total = 0
    for char in text:
        total += 2 if ord(char) > 0xFFFF else 1
        found.append(total)
    return found


def find_citations(text: str) -> list[dict[str, Any]]:
    if len(text) > MAX_CHARS:
        raise ValueError(f"the text has more than {MAX_CHARS} characters")
    at = utf16_offsets(text)
    rows: list[dict[str, Any]] = []
    for c in extract(text):
        clause = ""
        if c.clause_start is not None and c.clause_end is not None:
            clause = text[c.clause_start : c.clause_end]
        rows.append(
            {
                "start": at[c.start],
                "end": at[c.end],
                "text": c.text,
                "key": c.designation.key(),
                "base_key": c.designation.base_key(),
                "body": c.designation.body,
                "clause": clause,
                "inferred": c.inferred,
            }
        )
    return rows


def sample_text(seed: int) -> str:
    parts = []
    for item in generate(seed, SAMPLE_RFIS).rfis:
        rfi = item.rfi
        lines = [rfi.subject, rfi.question]
        if rfi.response:
            lines.append(rfi.response)
        parts.append("\n".join(lines))
    return "\n\n".join(parts)
