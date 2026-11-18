import csv
import html
import io
import json
import re
import unicodedata
from collections.abc import Iterable, Iterator, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from rfikit.analyze import MOST, AnalysisResult, analyze
from rfikit.io import atomic_text
from rfikit.notice import DISCLAIMER, LICENSE_LINE, OWNERS
from rfikit.textnorm import clip
from rfikit.types import Citation, Rfi

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


Json = dict[str, Any]

TOP_KEYS = 20
RATES_TITLE = "Extraction rates, measured on synthetic data"
NO_CITATIONS = "No citations found."
SYNTHETIC_NOTE = "The input is synthetic data."
SETS = (
    ("A", "Family A, report seeds"),
    ("B", "Family B, report seeds"),
    ("written", "Written set"),
)
METHODS = (
    ("rfikit", "rfikit"),
    ("naive", "naive baseline"),
    ("prototype", "prototype regexes"),
)
LEVELS = (
    ("strict", "strict span"),
    ("overlap", "overlap span"),
    ("full", "full key"),
    ("base", "base key"),
    ("clause", "clause"),
)
FILES = (
    "citations.csv: every citation found, one row each (the same columns as "
    "rfikit extract).",
    "analysis.md and analysis.html: the same tables, top base keys, counts per "
    "body, citations per RFI and the measured rates.",
    "README.txt: this file.",
)
STYLE = (
    "body{font-family:sans-serif;margin:1rem;line-height:1.4}"
    "main{max-width:60rem;margin:0 auto}"
    ".scroll{overflow-x:auto}"
    "table{border-collapse:collapse}"
    "th,td{border:1px solid #767676;padding:0.25rem 0.5rem;text-align:left}"
    "th{background:#eeeeee}"
)
CSP = (
    "default-src 'none'; style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'"
)
MD_SPECIAL = re.compile(r"([\\|`<>\[\]*_&!~])")
LINE_BREAKS = re.compile(r"[\r\n\x0b\x0c\x85\u2028\u2029]+")


@dataclass(frozen=True)
class Section:
    title: str
    note: str
    header: tuple[str, ...]
    rows: tuple[tuple[str, ...], ...]
    empty: str = NO_CITATIONS


def md_cell(text: str) -> str:
    return MD_SPECIAL.sub(r"\\\1", LINE_BREAKS.sub(" ", text))


def load_measured() -> Json:
    path = Path(__file__).with_name("measured.json")
    data: Json = json.loads(path.read_text(encoding="utf-8"))
    return data


def _rate(value: Any) -> str:
    if isinstance(value, bool) or not isinstance(value, int | float):
        return "n/a"
    return f"{value:.3f}"


def rate_rows(doc: Json) -> list[tuple[str, ...]]:
    sets = doc.get("full", {}).get("sets", {})
    rows: list[tuple[str, ...]] = []
    for set_key, set_name in SETS:
        methods = sets.get(set_key, {}).get("methods", {})
        for method_key, method_name in METHODS:
            levels = methods.get(method_key, {}).get("levels", {})
            for level_key, level_name in LEVELS:
                got = levels.get(level_key, {})
                cells = tuple(_rate(got.get(k)) for k in ("precision", "recall", "f1"))
                rows.append((method_name, set_name, level_name, *cells))
    return rows


def build_sections(result: AnalysisResult, doc: Json) -> list[Section]:
    total = result.citation_total
    with_cites = sum(m for n, m in result.per_rfi if n > 0)
    summary = Section(
        "Summary",
        "",
        ("Item", "Count"),
        (
            ("RFIs read", str(result.rfis_read)),
            ("Citations found", str(total)),
            ("RFIs with at least one citation", str(with_cites)),
        ),
    )
    top = tuple((k, str(n)) for k, n in result.key_counts[:TOP_KEYS])
    bodies = tuple((b, str(n)) for b, n in result.body_counts)
    sizes = tuple((str(n), str(m)) for n, m in result.per_rfi)
    most = tuple((clip(i), str(n)) for i, n in result.most)
    rates = Section(
        RATES_TITLE,
        str(doc.get("data", "")),
        ("Method", "Set", "Level", "Precision", "Recall", "F1"),
        tuple(rate_rows(doc)),
    )
    return [
        summary,
        Section(
            f"Top base keys (up to {TOP_KEYS})", "", ("Base key", "Citations"), top
        ),
        Section("Citations per body", "", ("Body", "Citations"), bodies),
        Section(
            "Citations per RFI",
            "How many RFIs have 0, 1, 2 and more citations.",
            ("Citations", "RFIs"),
            sizes,
            "No RFIs read.",
        ),
        Section(
            f"RFIs with the most citations (up to {MOST})",
            "",
            ("rfi_id", "Citations"),
            most,
        ),
        rates,
    ]


def _md_table(section: Section) -> list[str]:
    if not section.rows:
        return [md_cell(section.empty), ""]
    head = "| " + " | ".join(md_cell(h) for h in section.header) + " |"
    rule = "|" + "|".join("---" for _ in section.header) + "|"
    lines = [head, rule]
    for row in section.rows:
        lines.append("| " + " | ".join(md_cell(c) for c in row) + " |")
    lines.append("")
    return lines


def render_markdown(result: AnalysisResult, doc: Json) -> str:
    lines = ["# rfikit analysis", ""]
    if result.synthetic:
        lines += [SYNTHETIC_NOTE, ""]
    for section in build_sections(result, doc):
        lines += [f"## {md_cell(section.title)}", ""]
        if section.note:
            lines += [md_cell(section.note), ""]
        lines += _md_table(section)
    lines += ["## License", "", md_cell(LICENSE_LINE), ""]
    lines += ["## Disclaimer", "", md_cell(DISCLAIMER), "", md_cell(OWNERS), ""]
    return "\n".join(lines)


def _h(text: str) -> str:
    return html.escape(text, quote=True)


def _html_table(section: Section) -> list[str]:
    if not section.rows:
        return [f"<p>{_h(section.empty)}</p>"]
    label = _h(section.title)
    lines = [f'<div class="scroll" tabindex="0" role="region" aria-label="{label}">']
    lines.append("<table>")
    cells = "".join(f'<th scope="col">{_h(h)}</th>' for h in section.header)
    lines.append(f"<thead><tr>{cells}</tr></thead>")
    lines.append("<tbody>")
    for row in section.rows:
        lines.append("<tr>" + "".join(f"<td>{_h(c)}</td>" for c in row) + "</tr>")
    lines += ["</tbody>", "</table>", "</div>"]
    return lines


def render_html(result: AnalysisResult, doc: Json) -> str:
    lines = [
        "<!DOCTYPE html>",
        '<html lang="en">',
        "<head>",
        '<meta charset="utf-8">',
        f'<meta http-equiv="Content-Security-Policy" content="{_h(CSP)}">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        "<title>rfikit analysis</title>",
        f"<style>{STYLE}</style>",
        "</head>",
        "<body>",
        "<main>",
        "<h1>rfikit analysis</h1>",
    ]
    if result.synthetic:
        lines.append(f"<p>{_h(SYNTHETIC_NOTE)}</p>")
    for section in build_sections(result, doc):
        lines.append(f"<h2>{_h(section.title)}</h2>")
        if section.note:
            lines.append(f"<p>{_h(section.note)}</p>")
        lines += _html_table(section)
    lines += [
        "<h2>License</h2>",
        f"<p>{_h(LICENSE_LINE)}</p>",
        "<h2>Disclaimer</h2>",
        f"<p>{_h(DISCLAIMER)}</p>",
        f"<p>{_h(OWNERS)}</p>",
        "</main>",
        "</body>",
        "</html>",
        "",
    ]
    return "\n".join(lines)


def render_readme(result: AnalysisResult) -> str:
    lines: list[str] = []
    if result.synthetic:
        lines += ["Synthetic data. The input of this analysis is synthetic data.", ""]
    lines += ["rfikit analysis files", "", "Files"]
    lines += [f"- {text}" for text in FILES]
    lines += ["", "License", LICENSE_LINE, "", "Disclaimer", DISCLAIMER, OWNERS, ""]
    return "\n".join(lines)


def write_analysis(
    out: Path, result: AnalysisResult, protected: Sequence[Path] = ()
) -> None:
    doc = load_measured()
    texts = (
        ("analysis.md", render_markdown(result, doc)),
        ("analysis.html", render_html(result, doc)),
        ("README.txt", render_readme(result)),
    )
    for name, text in texts:
        with atomic_text(out / name, protected) as handle:
            handle.write(text)


def analyze_to(
    out: Path,
    rfis: Iterable[Rfi],
    synthetic: bool = False,
    protected: Sequence[Path] = (),
) -> AnalysisResult:
    batch: list[list[str]] = []
    with atomic_text(out / "citations.csv", protected) as handle:
        handle.write(csv_chunk([list(CITATION_HEADER)]))

        def add(rfi_id: str, c: Citation) -> None:
            batch.append(citation_row(rfi_id, c))
            if len(batch) >= BATCH:
                handle.write(csv_chunk(batch))
                batch.clear()

        result = analyze(rfis, synthetic, add)
        if batch:
            handle.write(csv_chunk(batch))
    write_analysis(out, result, protected)
    return result
