import csv
import io
import unicodedata
from collections.abc import Iterable, Sequence

LEADING = ("=", "+", "-", "@", "＝", "＋", "－", "＠")
CONTROL = ("\t", "\r", "\n")


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
