import re

from rfikit.evaluate import GoldCitation

DASHES = {chr(0x2010), chr(0x2011), chr(0x2012), chr(0x2212)}
DASH_MAP = {ord(ch): "-" for ch in DASHES}
SPACE_CHARS = " " + chr(0xA0) + chr(0x202F) + "\n\r\t"
CLAUSE_WORDS = r"(?:CLAUSE|SECTION|SEC\.|PARA|TABLE|FIGURE|ANNEX|RULE)"
PREFIX = re.compile(r"(?:IEEE|IEC|ANSI|NEMA|ASTM|STD|/)*")


def norm(text: str) -> str:
    text = text.translate(DASH_MAP)
    return "".join(ch for ch in text if ch not in SPACE_CHARS).upper()


def key_clause(key: str) -> str:
    match = re.search(r" (Clause|Table|Figure|Annex|Rule|Section) .*$", key)
    return match.group(0).strip() if match else ""


def key_core(key: str) -> str:
    cut = key[: len(key) - len(key_clause(key))].strip() if key_clause(key) else key
    return cut.split(" ", 1)[1] if " " in cut else ""


def is_bare(c: GoldCitation) -> bool:
    return c.clause_start is not None and c.clause_start == c.start


def expected_base(key: str) -> str:
    body = key.split(" ")[0]
    core = key[: len(key) - len(key_clause(key))].strip() if key_clause(key) else key
    if body == "NESC":
        clause = key_clause(key)
        return "NESC " + clause if clause else "NESC"
    if body == "IEC":
        return core.split(":")[0]
    if body == "ASTM":
        return re.sub(r"-\d{2}[a-z]?(?:e\d)?(?:\(\d{4}\))?$", "", core)
    return re.sub(r"-\d{4}$", "", core)


def check_key_matches_slice(c: GoldCitation, piece: str) -> bool:
    """Assert the key agrees with the text. True when fully checked."""
    body = c.key.split(" ")[0]
    if body == "NESC":
        year = re.search(r"\b(\d{4})\b", c.key)
        if not is_bare(c) and year:
            assert year.group(1) in norm(piece), c
        if not is_bare(c):
            assert (
                "NESC" in norm(piece)
                or "C2" in norm(piece)
                or (c.noise_class == "misspelled")
            ), c
        return False
    if c.noise_class == "misspelled":
        return False
    rest = norm(piece)
    core = norm(key_core(c.key))
    assert rest.endswith(core), (c, piece)
    prefix = rest[: len(rest) - len(core)]
    assert PREFIX.fullmatch(prefix), (c, piece)
    if c.inferred:
        assert prefix == "", c
    else:
        assert body in prefix, c
    return True
