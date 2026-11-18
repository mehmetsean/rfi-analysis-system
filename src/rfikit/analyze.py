from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass

from rfikit.cite import extract_rfi
from rfikit.types import Citation, Rfi

MOST = 10


@dataclass(frozen=True)
class AnalysisResult:
    rfis_read: int
    citations: tuple[tuple[str, Citation], ...]
    key_counts: tuple[tuple[str, int], ...]
    body_counts: tuple[tuple[str, int], ...]
    per_rfi: tuple[tuple[int, int], ...]
    most: tuple[tuple[str, int], ...]
    synthetic: bool


def _ranked(counts: Counter[str]) -> tuple[tuple[str, int], ...]:
    return tuple(sorted(counts.items(), key=lambda item: (-item[1], item[0])))


def analyze(rfis: Iterable[Rfi], synthetic: bool = False) -> AnalysisResult:
    citations: list[tuple[str, Citation]] = []
    keys: Counter[str] = Counter()
    bodies: Counter[str] = Counter()
    sizes: Counter[int] = Counter()
    per_id: Counter[str] = Counter()
    read = 0
    for rfi in rfis:
        read += 1
        found = extract_rfi(rfi)
        sizes[len(found)] += 1
        if found:
            per_id[rfi.rfi_id] = len(found)
        for c in found:
            citations.append((rfi.rfi_id, c))
            keys[c.designation.base_key()] += 1
            bodies[c.designation.body] += 1
    return AnalysisResult(
        rfis_read=read,
        citations=tuple(citations),
        key_counts=_ranked(keys),
        body_counts=_ranked(bodies),
        per_rfi=tuple(sorted(sizes.items())),
        most=_ranked(per_id)[:MOST],
        synthetic=synthetic,
    )
