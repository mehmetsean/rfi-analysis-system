import csv
import io
from collections.abc import Iterable, Sequence

DANGEROUS = ("=", "+", "-", "@", "\t", "\r")


def escape_cell(value: str) -> str:
    if value.startswith(DANGEROUS):
        return "'" + value
    return value


def csv_text(header: Sequence[str], rows: Iterable[Sequence[str]]) -> str:
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow([escape_cell(cell) for cell in header])
    for row in rows:
        writer.writerow([escape_cell(cell) for cell in row])
    return buffer.getvalue()
