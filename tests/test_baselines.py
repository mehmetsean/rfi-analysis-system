from prototype_baseline import STANDARDS_PATTERNS, Span, naive_spans, prototype_spans


def texts(text: str, spans: list[Span]) -> list[str]:
    return [text[s[1] : s[2]] for s in spans]


def test_prototype_has_six_groups() -> None:
    assert list(STANDARDS_PATTERNS) == ["IEEE", "ANSI", "NESC", "IEC", "ASTM", "NEMA"]
    assert sum(len(v) for v in STANDARDS_PATTERNS.values()) == 8


def test_prototype_finds_plain_forms() -> None:
    text = "IEEE 1547-2018 and ASTM A123 and NEMA MG 1 and IEC 60076-1"
    assert texts(text, prototype_spans(text)) == [
        "IEEE 1547-2018",
        "ASTM A123",
        "NEMA MG 1",
        "IEC 60076-1",
    ]


def test_prototype_keeps_its_known_flaws() -> None:
    text = "Rule 232 of the contract and IEEE C57.12.00-2015"
    found = texts(text, prototype_spans(text))
    assert "Rule 232" in found
    assert "IEEE 80" not in found
    assert prototype_spans("IEEE C57.12.00-2015") == [("IEEE", 0, len("IEEE C57.12"))]


def test_prototype_has_no_normalization() -> None:
    spans = prototype_spans("ieee 1547")
    assert [(s.body, s.start, s.end) for s in spans] == [("IEEE", 0, 9)]


def test_naive_takes_the_next_token() -> None:
    text = "see ASTM A123/A123M-17, then NESC and NEMA 4X."
    assert texts(text, naive_spans(text)) == ["ASTM A123/A123M-17", "NESC", "NEMA 4X"]


def test_naive_body_at_end_of_text() -> None:
    assert naive_spans("per IEEE") == [("IEEE", 4, 8)]
