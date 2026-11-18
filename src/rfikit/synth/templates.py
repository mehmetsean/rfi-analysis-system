import re
from dataclasses import dataclass

SLOT = re.compile(r"\{([a-z])([0-9]?)\}")
CITE_KINDS = ("c", "w", "y", "e", "n", "l", "b", "o")
NEGATIVE_KINDS = ("x", "k")
TEXT_KINDS = ("p", "d", "i", "r", "a", "g")
SLOT_KINDS = CITE_KINDS + NEGATIVE_KINDS + TEXT_KINDS
ISSUE_TYPES = (
    "design_clarification",
    "missing_information",
    "document_conflict",
    "substitution_request",
    "field_condition",
    "standard_applicability",
)


@dataclass(frozen=True)
class Template:
    template_id: str
    family: str
    issue_type: str
    subject: str
    question: str
    response: str = ""


def slot_names(text: str) -> list[str]:
    return [m.group(1) + m.group(2) for m in SLOT.finditer(text)]


def split_slots(text: str) -> list[tuple[str, str]]:
    parts: list[tuple[str, str]] = []
    last = 0
    for match in SLOT.finditer(text):
        if match.start() > last:
            parts.append(("text", text[last : match.start()]))
        parts.append(("slot", match.group(1) + match.group(2)))
        last = match.end()
    if last < len(text):
        parts.append(("text", text[last:]))
    return parts
