from collections import Counter
from collections.abc import Callable, Iterable
from dataclasses import dataclass

from rfikit.cite import extract_rfi
from rfikit.textnorm import clip
from rfikit.types import Citation, Rfi

MOST = 10

Sink = Callable[[str, Citation], None]


@dataclass(frozen=True)
class AnalysisResult:
    rfis_read: int
    citation_total: int
    key_counts: tuple[tuple[str, int], ...]
    body_counts: tuple[tuple[str, int], ...]
    per_rfi: tuple[tuple[int, int], ...]
    most: tuple[tuple[str, int], ...]
    synthetic: bool


def _ranked(counts: Counter[str]) -> tuple[tuple[str, int], ...]:
    return tuple(sorted(counts.items(), key=lambda item: (-item[1], item[0])))


def analyze(
    rfis: Iterable[Rfi], synthetic: bool = False, sink: Sink | None = None
) -> AnalysisResult:
    keys: Counter[str] = Counter()
    bodies: Counter[str] = Counter()
    sizes: Counter[int] = Counter()
    per_id: Counter[str] = Counter()
    seen: set[str] = set()
    total = 0
    for rfi in rfis:
        if rfi.rfi_id in seen:
            raise ValueError(
                f"rfi_id {clip(rfi.rfi_id)} repeats, give each RFI a unique rfi_id"
            )
        seen.add(rfi.rfi_id)
        found = extract_rfi(rfi)
        sizes[len(found)] += 1
        total += len(found)
        if found:
            per_id[rfi.rfi_id] = len(found)
        for c in found:
            if sink is not None:
                sink(rfi.rfi_id, c)
            keys[c.designation.base_key()] += 1
            bodies[c.designation.body] += 1
    return AnalysisResult(
        rfis_read=len(seen),
        citation_total=total,
        key_counts=_ranked(keys),
        body_counts=_ranked(bodies),
        per_rfi=tuple(sorted(sizes.items())),
        most=_ranked(per_id)[:MOST],
        synthetic=synthetic,
    )
