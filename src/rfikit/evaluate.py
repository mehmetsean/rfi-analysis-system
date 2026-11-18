import csv
import io
from dataclasses import dataclass
from pathlib import Path

COLUMNS = ("subject", "question", "response")
SCOPES = ("in", "out")
CATALOG_VALUES = ("real", "invented")
NOISE_CLASSES = (
    "",
    "misspelled",
    "list_continuation",
    "line_break",
    "unicode_dash",
    "spacing",
    "case",
)
ISSUE_TYPES = (
    "design_clarification",
    "missing_information",
    "document_conflict",
    "substitution_request",
    "field_condition",
    "standard_applicability",
)
NEGATIVE_KINDS = (
    "ieee_transactions",
    "rfi_number",
    "kva_rating",
    "bare_rule",
    "bare_nesc_no_context",
    "room_number",
    "sheet_number",
    "ip_rating",
    "drawing_number",
    "ansi_color",
    "ansi_class",
    "ansi_sheet",
    "astm_grade",
    "part_number",
    "nema_enclosure",
    "nema_plug",
    "nema_size",
    "nema_premium",
    "date",
    "spec_section",
)

CITATION_HEADER = (
    "rfi_id",
    "column",
    "start",
    "end",
    "clause_start",
    "clause_end",
    "key",
    "base_key",
    "scope",
    "inferred",
    "catalog",
    "noise_class",
)
NEGATIVE_HEADER = ("rfi_id", "column", "start", "end", "kind")
RFI_HEADER = ("rfi_id", "issue_type", "group_id", "template_id", "family")


class LabelError(ValueError):
    pass


@dataclass(frozen=True)
class GoldCitation:
    rfi_id: str
    column: str
    start: int
    end: int
    clause_start: int | None
    clause_end: int | None
    key: str
    base_key: str
    scope: str
    inferred: bool
    catalog: str
    noise_class: str


@dataclass(frozen=True)
class GoldNegative:
    rfi_id: str
    column: str
    start: int
    end: int
    kind: str


@dataclass(frozen=True)
class RfiLabel:
    rfi_id: str
    issue_type: str
    group_id: str
    template_id: str
    family: str


class _Row:
    def __init__(self, path: Path, line: int, values: dict[str, str]) -> None:
        self.path = path
        self.line = line
        self.values = values

    def fail(self, name: str, message: str) -> LabelError:
        return LabelError(
            f"{self.path.name} line {self.line}, column {name}: {message}"
        )

    def text(self, name: str) -> str:
        return self.values[name]

    def required(self, name: str) -> str:
        value = self.values[name]
        if value == "":
            raise self.fail(name, "value is empty")
        return value

    def integer(self, name: str) -> int:
        value = self.values[name]
        try:
            number = int(value)
        except ValueError:
            raise self.fail(name, f"not an integer: {value!r}") from None
        if number < 0:
            raise self.fail(name, f"negative offset: {number}")
        return number

    def optional_integer(self, name: str) -> int | None:
        if self.values[name] == "":
            return None
        return self.integer(name)

    def choice(self, name: str, allowed: tuple[str, ...]) -> str:
        value = self.values[name]
        if value not in allowed:
            raise self.fail(name, f"unknown value {value!r}, allowed: {list(allowed)}")
        return value

    def span(self) -> tuple[int, int]:
        start = self.integer("start")
        end = self.integer("end")
        if end <= start:
            raise self.fail("end", f"end {end} is not after start {start}")
        return start, end


def _read_rows(path: Path, header: tuple[str, ...]) -> list[_Row]:
    try:
        text = path.read_text(encoding="utf-8", newline="")
    except UnicodeDecodeError:
        raise LabelError(f"{path.name}: file is not valid UTF-8") from None
    if text.startswith("\ufeff"):
        raise LabelError(f"{path.name}: file starts with a BOM, save it without one")
    reader = csv.reader(io.StringIO(text, newline=""), strict=True)
    try:
        first = next(reader, None)
        if first is None:
            raise LabelError(f"{path.name}: file is empty")
        for name in header:
            if name not in first:
                raise LabelError(f"{path.name}: missing column {name!r}")
        rows: list[_Row] = []
        for cells in reader:
            line = reader.line_num
            if len(cells) != len(first):
                raise LabelError(
                    f"{path.name} line {line}: expected {len(first)} cells, "
                    f"got {len(cells)}"
                )
            rows.append(_Row(path, line, dict(zip(first, cells, strict=True))))
    except csv.Error as error:
        raise LabelError(f"{path.name}: bad CSV: {error}") from None
    return rows


def read_citations(path: Path) -> list[GoldCitation]:
    result: list[GoldCitation] = []
    for row in _read_rows(path, CITATION_HEADER):
        start, end = row.span()
        clause_start = row.optional_integer("clause_start")
        clause_end = row.optional_integer("clause_end")
        if (clause_start is None) != (clause_end is None):
            raise row.fail("clause_end", "clause_start and clause_end go together")
        if clause_start is not None and clause_end is not None:
            if clause_end <= clause_start:
                raise row.fail("clause_end", "clause end is not after clause start")
        result.append(
            GoldCitation(
                rfi_id=row.required("rfi_id"),
                column=row.choice("column", COLUMNS),
                start=start,
                end=end,
                clause_start=clause_start,
                clause_end=clause_end,
                key=row.required("key"),
                base_key=row.required("base_key"),
                scope=row.choice("scope", SCOPES),
                inferred=row.choice("inferred", ("0", "1")) == "1",
                catalog=row.choice("catalog", CATALOG_VALUES),
                noise_class=row.choice("noise_class", NOISE_CLASSES),
            )
        )
    return result


def read_negatives(path: Path) -> list[GoldNegative]:
    result: list[GoldNegative] = []
    for row in _read_rows(path, NEGATIVE_HEADER):
        start, end = row.span()
        result.append(
            GoldNegative(
                rfi_id=row.required("rfi_id"),
                column=row.choice("column", COLUMNS),
                start=start,
                end=end,
                kind=row.choice("kind", NEGATIVE_KINDS),
            )
        )
    return result


def read_rfi_labels(path: Path) -> list[RfiLabel]:
    result: list[RfiLabel] = []
    for row in _read_rows(path, RFI_HEADER):
        result.append(
            RfiLabel(
                rfi_id=row.required("rfi_id"),
                issue_type=row.choice("issue_type", ISSUE_TYPES),
                group_id=row.required("group_id"),
                template_id=row.text("template_id"),
                family=row.required("family"),
            )
        )
    return result
