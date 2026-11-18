import re
from typing import NamedTuple

# Six regex groups of the 2025 prototype, unchanged. Only findall became finditer.
STANDARDS_PATTERNS = {
    "IEEE": [
        r"IEEE[-\s]?(\d{3,4}(?:\.\d+)?(?:-\d{4})?)",
        r"IEEE[-\s]?C(\d{2,3}\.\d+(?:-\d{4})?)",
    ],
    "ANSI": [r"ANSI[-\s]?([A-Z]?\d{2,3}\.?\d*(?:[-\.]\d+)?)"],
    "NESC": [
        r"NESC[-\s]?(?:RULE[-\s]?)?(\d{3}[A-Z]?\d?)",
        r"RULE[-\s]?(\d{3}[A-Z]?\d?)",
    ],
    "IEC": [r"IEC[-\s]?(\d{4,5}(?:[-\.]\d+)?(?::\d{4})?)"],
    "ASTM": [r"ASTM[-\s]?([A-Z]?\d{2,4})"],
    "NEMA": [r"NEMA[-\s]?([A-Z]{2,3}[-\s]?\d+)"],
}

BODIES = ("IEEE", "NESC", "IEC", "ANSI", "ASTM", "NEMA")
_BODY_TOKEN = re.compile(
    r"(?<![A-Za-z0-9])(?:IEEE|NESC|IEC|ANSI|ASTM|NEMA)(?![A-Za-z])", re.I
)
_NEXT_TOKEN = re.compile(r"[ \t\r\n]+([^\s]+)")


class Span(NamedTuple):
    body: str
    start: int
    end: int


def prototype_spans(text: str) -> list[Span]:
    found: list[Span] = []
    for body, patterns in STANDARDS_PATTERNS.items():
        for pattern in patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                found.append(Span(body, match.start(), match.end()))
    found.sort(key=lambda s: (s.start, s.end, s.body))
    return found


def naive_spans(text: str) -> list[Span]:
    # Body token plus the next token; NESC alone is already a citation.
    found: list[Span] = []
    for match in _BODY_TOKEN.finditer(text):
        body = match.group(0).upper()
        end = match.end()
        if body != "NESC":
            following = _NEXT_TOKEN.match(text, end)
            if following:
                end = following.end(1)
                while end > following.start(1) and text[end - 1] in ".,;:)":
                    end -= 1
        found.append(Span(body, match.start(), end))
    return found
