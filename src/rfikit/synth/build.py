from rfikit.synth.cites import CiteSpec, ListSpec
from rfikit.synth.model import CitationLabel, NegativeLabel
from rfikit.synth.negatives import NegSpec


class Builder:
    """Builds one column and records where each item is inserted."""

    def __init__(self, column: str) -> None:
        self.column = column
        self.citations: list[CitationLabel] = []
        self.negatives: list[NegativeLabel] = []
        self._parts: list[str] = []
        self._size = 0

    @property
    def text(self) -> str:
        return "".join(self._parts)

    def add_text(self, text: str) -> None:
        self._parts.append(text)
        self._size += len(text)

    def add_cite(self, spec: CiteSpec) -> str:
        began = self._size
        item = spec.rendered
        clause = spec.clause
        clause_span: tuple[int, int] | None = None
        span: tuple[int, int]
        if item.inferred and clause is not None:
            start = self._size
            self.add_text(clause.text)
            span = clause_span = (start, self._size)
        else:
            if clause is not None and spec.clause_first:
                clause_span = self._clause(clause.text)
                self.add_text(spec.connector)
            start = self._size
            self.add_text(item.text)
            span = (start, self._size)
            if clause is not None and not spec.clause_first:
                self.add_text(spec.connector)
                clause_span = self._clause(clause.text)
        self.citations.append(self._label(spec, span, clause_span))
        return self.text[began : self._size]

    def add_list(self, spec: ListSpec) -> str:
        began = self._size
        self.add_cite(spec.items[0])
        for sep, item in zip(spec.separators, spec.items[1:], strict=True):
            self.add_text(sep)
            self.add_cite(item)
        return self.text[began : self._size]

    def add_negative(self, spec: NegSpec) -> str:
        began = self._size
        self.add_text(spec.prefix)
        start = self._size
        self.add_text(spec.text)
        self.negatives.append(
            NegativeLabel(self.column, start, self._size, spec.text, spec.kind)
        )
        self.add_text(spec.suffix)
        return self.text[began : self._size]

    def _clause(self, text: str) -> tuple[int, int]:
        start = self._size
        self.add_text(text)
        return start, self._size

    def _label(
        self,
        spec: CiteSpec,
        span: tuple[int, int],
        clause_span: tuple[int, int] | None,
    ) -> CitationLabel:
        item = spec.rendered
        designation = item.designation
        return CitationLabel(
            column=self.column,
            start=span[0],
            end=span[1],
            text=item.text
            if not item.inferred or spec.clause is None
            else spec.clause.text,
            clause_start=clause_span[0] if clause_span else None,
            clause_end=clause_span[1] if clause_span else None,
            key=designation.key(),
            base_key=designation.base_key(),
            scope=item.scope,
            inferred=item.inferred,
            catalog=item.catalog,
            noise_class=spec.noise_class,
        )
