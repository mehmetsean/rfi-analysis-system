import csv
import io
import unicodedata
from collections.abc import Iterable, Iterator, Sequence

from rfikit.types import Citation

LEADING = ("=", "+", "-", "@", "＝", "＋", "－", "＠")
CONTROL = ("\t", "\r", "\n")
BATCH = 1000
CITATION_HEADER = (
    "rfi_id",
    "column",
    "start",
    "end",
    "text",
    "key",
    "base_key",
    "body",
    "clause_start",
    "clause_end",
    "inferred",
)


def _skipped(char: str) -> bool:
    return char.isspace() or unicodedata.category(char) in ("Cf", "Cc")


def escape_cell(value: str) -> str:
    start = 0
    while start < len(value) and _skipped(value[start]):
        start += 1
    if value.startswith(CONTROL) or value[start:].startswith(LEADING):
        return "'" + value
    return value


def csv_chunk(rows: Iterable[Sequence[str]]) -> str:
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    for row in rows:
        writer.writerow([escape_cell(cell) for cell in row])
    return buffer.getvalue()


def csv_text(header: Sequence[str], rows: Iterable[Sequence[str]]) -> str:
    return csv_chunk([header]) + csv_chunk(rows)


def _number(value: int | None) -> str:
    return "" if value is None else str(value)


def citation_row(rfi_id: str, c: Citation) -> list[str]:
    d = c.designation
    return [
        rfi_id,
        c.column,
        str(c.start),
        str(c.end),
        c.text,
        d.key(),
        d.base_key(),
        d.body,
        _number(c.clause_start),
        _number(c.clause_end),
        "1" if c.inferred else "0",
    ]


def csv_batches(rows: Iterable[list[str]]) -> Iterator[str]:
    batch: list[list[str]] = []
    for row in rows:
        batch.append(row)
        if len(batch) >= BATCH:
            yield csv_chunk(batch)
            batch = []
    if batch:
        yield csv_chunk(batch)
