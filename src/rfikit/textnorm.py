import re

_DASH_CODES = (0x2010, 0x2011, 0x2012, 0x2013, 0x2014, 0x2015, 0x2212)
_SPACE_CODES = (0xA0, 0x1680, 0x202F, 0x205F, 0x3000) + tuple(range(0x2000, 0x200B))
_BREAK_CODES = (0x85, 0x2028, 0x2029)

_TABLE: dict[int, str] = {}
for _code in _DASH_CODES:
    _TABLE[_code] = "-"
for _code in _SPACE_CODES:
    _TABLE[_code] = " "
for _code in _BREAK_CODES:
    _TABLE[_code] = "\n"

_WORD = re.compile(r"[ \t\r\n]*([A-Za-z]+)", re.ASCII)


def clean(text: str) -> str:
    return text.translate(_TABLE)


def word_at(text: str, pos: int) -> str:
    match = _WORD.match(text, pos)
    return match.group(1).lower() if match else ""


MAX_SHOWN = 40


def clip(value: str) -> str:
    text = repr(value[:MAX_SHOWN])
    if len(value) > MAX_SHOWN:
        text = text[:-1] + "..." + text[-1]
    return text
