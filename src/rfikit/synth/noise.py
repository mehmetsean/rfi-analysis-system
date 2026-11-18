from rfikit.synth.forms import Rendered
from rfikit.synth.rng import Rng

DASHES = tuple(chr(code) for code in (0x2010, 0x2011, 0x2012, 0x2212))
BREAKS = ("\n", "\r\n", "\n  ")
SPACES = (chr(0xA0), chr(0x202F))
MISSPELLINGS = {
    "IEEE": ("IEE", "IEEEE"),
    "IEC": ("IE", "ICE"),
    "ANSI": ("ANS", "ASNI"),
    "ASTM": ("ASMT", "ATSM"),
    "NEMA": ("NEM", "NEAM"),
    "NESC": ("NSEC", "NECS"),
}
NOISE_ORDER = ("misspelled", "line_break", "unicode_dash", "spacing", "case")


def _break_points(item: Rendered) -> list[tuple[str, int]]:
    points: list[tuple[str, int]] = []
    if item.number_at <= 0:
        return points
    points.append(("gap", item.number_at - 1))
    for i in range(item.number_at, len(item.text) - 1):
        if item.text[i] in ".-":
            points.append(("after", i))
    return points


def _spacing_variants(item: Rendered) -> list[str]:
    text = item.text
    variants: list[str] = []
    if " " in text:
        variants.extend(["double", "nbsp"])
    at = item.number_at
    if at > 1 and text[at].isdigit() and text[at - 2].isalpha():
        variants.append("missing")
    if at > 0 and text[at].isalpha() and text[at + 1 : at + 2].isdigit():
        variants.append("inside")
    return variants


def eligible(item: Rendered) -> list[str]:
    if item.inferred:
        return []
    found = ["misspelled"] if item.word[0] >= 0 else []
    if _break_points(item):
        found.append("line_break")
    if "-" in item.text:
        found.append("unicode_dash")
    if _spacing_variants(item):
        found.append("spacing")
    if item.word[0] >= 0:
        found.append("case")
    return found


def _misspell(rng: Rng, item: Rendered) -> str:
    start, end = item.word
    text = item.text
    zero = text.find("0", max(item.number_at, 0)) if item.number_at >= 0 else -1
    if zero >= 0 and rng.chance(0.4):
        return text[:zero] + "O" + text[zero + 1 :]
    return text[:start] + rng.pick(MISSPELLINGS[text[start:end]]) + text[end:]


def _line_break(rng: Rng, item: Rendered) -> str:
    kind, at = rng.pick(_break_points(item))
    mark = rng.pick(BREAKS)
    text = item.text
    if kind == "gap":
        return text[:at] + mark + text[at + 1 :]
    return text[: at + 1] + mark + text[at + 1 :]


def _spacing(rng: Rng, item: Rendered) -> str:
    text = item.text
    variant = rng.pick(_spacing_variants(item))
    if variant == "double":
        at = text.index(" ")
        return text[:at] + "  " + text[at + 1 :]
    if variant == "nbsp":
        at = text.index(" ")
        return text[:at] + rng.pick(SPACES) + text[at + 1 :]
    if variant == "missing":
        at = item.number_at - 1
        return text[:at] + text[at + 1 :]
    at = item.number_at + 1
    return text[:at] + " " + text[at:]


def _case(rng: Rng, item: Rendered) -> str:
    start, end = item.word
    if rng.chance(0.5):
        return item.text.lower()
    word = item.text[start:end]
    return item.text[:start] + word.capitalize() + item.text[end:]


def apply_noise(rng: Rng, item: Rendered, noise_class: str) -> str:
    if noise_class == "misspelled":
        return _misspell(rng, item)
    if noise_class == "line_break":
        return _line_break(rng, item)
    if noise_class == "unicode_dash":
        return item.text.replace("-", rng.pick(DASHES))
    if noise_class == "spacing":
        return _spacing(rng, item)
    if noise_class == "case":
        return _case(rng, item)
    raise ValueError(f"unknown noise class: {noise_class}")
