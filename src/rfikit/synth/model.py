from dataclasses import dataclass

from rfikit.synth.params import GenParams
from rfikit.types import Rfi


@dataclass(frozen=True)
class CitationLabel:
    column: str
    start: int
    end: int
    text: str
    clause_start: int | None
    clause_end: int | None
    key: str
    base_key: str
    scope: str
    inferred: bool
    catalog: str
    noise_class: str


@dataclass(frozen=True)
class NegativeLabel:
    column: str
    start: int
    end: int
    text: str
    kind: str


@dataclass(frozen=True)
class GeneratedRfi:
    rfi: Rfi
    template_id: str
    family: str
    citations: tuple[CitationLabel, ...]
    negatives: tuple[NegativeLabel, ...]


@dataclass(frozen=True)
class Corpus:
    seed: int
    n: int
    params: GenParams
    rfis: tuple[GeneratedRfi, ...]
