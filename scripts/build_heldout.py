"""Build the written held-out set from heldout/source.txt.

The script only strips markup and computes offsets. It does not import any
extraction code and it never computes keys: keys are written by hand.

Source format, one RFI per block:

    === W001 | issue_type | group_id
    subject: text
    question: text
    response: text

group_id "-" means "single-" plus the rfi_id. The response line is optional.
Lines starting with # and blank lines are ignored.

Inside a field value:

    [[c KEY | BASE | FLAGS | BODY]]   one citation
    [[n KIND | BODY]]                 one hard negative

FLAGS are words: real or invented (one is required), out, inferred and
noise=CLASS. BODY is the text. Without marks the whole BODY is the span.
<s>..</s> marks the span and <k>..</k> marks the clause. A body with only
<k> is allowed for an inferred citation: the clause is also the span.
Escapes: \\n, \\r, \\\\, \\uXXXX and \\UXXXXXXXX.
Surrogates, U+2013 and U+2014 are rejected.
"""

import csv
import hashlib
import io
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE_PATH = "heldout/source.txt"
COLUMNS = ("subject", "question", "response")
BANNED = (chr(0x2013), chr(0x2014))
TAG = re.compile(r"(</?[sk]>)")
ESCAPE = re.compile(r"\\(n|r|\\|u[0-9a-fA-F]{4}|U[0-9a-fA-F]{8})")

README_LINES = [
    "Written held-out set for rfikit (synthetic data)",
    "",
    "All data in this folder is synthetic. The RFIs were written by hand for this",
    "repository. Project codes, role ids and disciplines are invented. No real",
    "company, facility, project or person appears, and nothing comes from any",
    "employer. Only standard designations and clause numbers appear, never titles",
    "or standard text.",
    "",
    "Files",
    "- input/rfis.csv: rfi_id, subject, question, response.",
    "- labels/citations.csv, labels/negatives.csv, labels/rfis.csv: the labels.",
    '  In labels/rfis.csv the template_id is empty and the family is "written".',
    "- source.txt: the marked-up text the files above are built from.",
    "- manifest.json: sha256 of the source, each input, label and README file,",
    "  and counts.",
    "- CHANGES.md: label fixes made after the first commit.",
    "Rules for the labels are in docs/annotation_guide.md. One annotator labeled",
    "the set, so there is no agreement measure.",
    "Rebuild and check with: python scripts/build_heldout.py --check",
    "",
    "License",
    "All rights reserved. You may view the code and run it to evaluate it. "
    "Commercial use needs a paid license from Mehmet Tuzunkan: "
    "https://www.linkedin.com/in/mstuzunkan",
    "",
    "Disclaimer",
    "Decision support only, not legal, engineering, tax, accounting or assurance "
    "advice. No guarantee of compliance. rfikit does not say whether a standard "
    "applies or what it requires; check every citation against the official "
    "standard. False positives and misses are expected.",
    "The names IEEE, NESC, IEC, ANSI, ASTM and NEMA are used only to identify "
    "their documents. The names belong to their owners. This project has no "
    "affiliation with or endorsement from any of them.",
]
README_TEXT = "\n".join(README_LINES) + "\n"


class BuildError(ValueError):
    pass


@dataclass
class CitationMark:
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


@dataclass
class NegativeMark:
    start: int
    end: int
    kind: str


@dataclass
class ParsedColumn:
    text: str = ""
    citations: list[CitationMark] = field(default_factory=list)
    negatives: list[NegativeMark] = field(default_factory=list)


@dataclass
class ParsedRfi:
    rfi_id: str
    issue_type: str
    group_id: str
    columns: dict[str, ParsedColumn]


def _code_point(number: int, raw: str) -> str:
    if 0xD800 <= number <= 0xDFFF or number > 0x10FFFF:
        raise BuildError(f"escape U+{number:04X} is not a valid character in {raw!r}")
    return chr(number)


def unescape(raw: str) -> str:
    position = 0
    pieces: list[str] = []
    while position < len(raw):
        slash = raw.find("\\", position)
        if slash < 0:
            pieces.append(raw[position:])
            break
        pieces.append(raw[position:slash])
        match = ESCAPE.match(raw, slash)
        if match is None:
            raise BuildError(f"bad escape in {raw!r}")
        code = match.group(1)
        if code == "n":
            pieces.append("\n")
        elif code == "r":
            pieces.append("\r")
        elif code == "\\":
            pieces.append("\\")
        else:
            pieces.append(_code_point(int(code[1:], 16), raw))
        position = match.end()
    return "".join(pieces)


def _walk_body(
    body: str, base: int
) -> tuple[str, tuple[int, int] | None, tuple[int, int] | None]:
    if body != body.strip():
        raise BuildError(f"body has leading or trailing space: {body!r}")
    parts = TAG.split(body)
    text = ""
    spans: dict[str, tuple[int, int]] = {}
    opened: tuple[str, int] | None = None
    for part in parts:
        if TAG.fullmatch(part):
            name = part.strip("</>")
            if part.startswith("</"):
                if opened is None or opened[0] != name:
                    raise BuildError(f"closing {part} without opening: {body!r}")
                spans[name] = (opened[1], base + len(text))
                opened = None
            else:
                if opened is not None:
                    raise BuildError(f"nested {part}: {body!r}")
                if name in spans:
                    raise BuildError(f"two <{name}> marks: {body!r}")
                opened = (name, base + len(text))
        else:
            text += unescape(part)
    if opened is not None:
        raise BuildError(f"unclosed <{opened[0]}>: {body!r}")
    return text, spans.get("s"), spans.get("k")


def _check_span(full: str, base: int, span: tuple[int, int]) -> None:
    piece = full[span[0] - base : span[1] - base]
    if piece == "" or piece != piece.strip():
        raise BuildError(f"span is empty or touches a space: {piece!r}")


def _parse_flags(words: list[str]) -> tuple[str, bool, str, str]:
    scope = "in"
    inferred = False
    catalog = ""
    noise = ""
    for word in words:
        if word == "out":
            scope = "out"
        elif word == "inferred":
            inferred = True
        elif word in ("real", "invented"):
            if catalog:
                raise BuildError(f"two catalog flags: {words}")
            catalog = word
        elif word.startswith("noise=") and not noise:
            noise = word[len("noise=") :]
        else:
            raise BuildError(f"bad flag {word!r}")
    if not catalog:
        raise BuildError(f"flags need real or invented: {words}")
    return scope, inferred, catalog, noise


def _read_mark(inner: str, base: int, column: ParsedColumn) -> str:
    if len(inner) < 3 or inner[0] not in "cn" or inner[1] != " ":
        raise BuildError(f"mark must start with 'c ' or 'n ': {inner!r}")
    fields = inner[2:].split("|")
    if inner[0] == "n":
        if len(fields) != 2 or not fields[1].startswith(" "):
            raise BuildError(f"negative needs 'KIND | BODY': {inner!r}")
        text, span, clause = _walk_body(fields[1][1:], base)
        if span is not None or clause is not None:
            raise BuildError(f"negative takes no <s> or <k>: {inner!r}")
        _check_span(text, base, (base, base + len(text)))
        if not fields[0].strip():
            raise BuildError(f"negative needs a kind: {inner!r}")
        column.negatives.append(NegativeMark(base, base + len(text), fields[0].strip()))
        return text
    if len(fields) != 4 or not fields[3].startswith(" "):
        raise BuildError(f"citation needs 'KEY | BASE | FLAGS | BODY': {inner!r}")
    if not fields[0].strip() or not fields[1].strip():
        raise BuildError(f"citation needs a key and a base key: {inner!r}")
    scope, inferred, catalog, noise = _parse_flags(fields[2].split())
    text, span, clause = _walk_body(fields[3][1:], base)
    if span is None and clause is None:
        span = (base, base + len(text))
    elif span is None:
        if not inferred:
            raise BuildError(f"clause-only body needs the inferred flag: {inner!r}")
        span = clause
    if span is None:
        raise BuildError(f"no span in {inner!r}")
    _check_span(text, base, span)
    if clause is not None:
        _check_span(text, base, clause)
    column.citations.append(
        CitationMark(
            span[0],
            span[1],
            None if clause is None else clause[0],
            None if clause is None else clause[1],
            fields[0].strip(),
            fields[1].strip(),
            scope,
            inferred,
            catalog,
            noise,
        )
    )
    return text


def parse_column(raw: str) -> ParsedColumn:
    column = ParsedColumn()
    position = 0
    while position < len(raw):
        open_at = raw.find("[[", position)
        close_at = raw.find("]]", position)
        if close_at >= 0 and (open_at < 0 or close_at < open_at):
            raise BuildError(f"stray ']]' in {raw!r}")
        if open_at < 0:
            column.text += unescape(raw[position:])
            break
        column.text += unescape(raw[position:open_at])
        if close_at < 0:
            raise BuildError(f"unclosed '[[' in {raw!r}")
        inner = raw[open_at + 2 : close_at]
        if "[[" in inner:
            raise BuildError(f"nested '[[' in {raw!r}")
        column.text += _read_mark(inner, len(column.text), column)
        position = close_at + 2
    for banned in BANNED:
        if banned in column.text:
            raise BuildError(f"banned character U+{ord(banned):04X} in {raw!r}")
    return column


def parse_source(source: str) -> list[ParsedRfi]:
    rfis: list[ParsedRfi] = []
    raw_fields: dict[str, str] = {}
    field_lines: dict[str, int] = {}
    header: list[str] = []

    def finish() -> None:
        if not header:
            return
        for needed in ("subject", "question"):
            if needed not in raw_fields:
                raise BuildError(f"{header[0]}: missing {needed}")
        columns: dict[str, ParsedColumn] = {}
        for name in COLUMNS:
            try:
                columns[name] = parse_column(raw_fields.get(name, ""))
            except BuildError as error:
                where = field_lines.get(name, 0)
                raise BuildError(
                    f"{header[0]} {name} (source line {where}): {error}"
                ) from None
        group = header[2] if header[2] != "-" else "single-" + header[0]
        rfis.append(ParsedRfi(header[0], header[1], group, columns))

    for number, line in enumerate(source.splitlines(), start=1):
        if line.strip() == "" or line.startswith("#"):
            continue
        if line.startswith("=== "):
            finish()
            header = [part.strip() for part in line[4:].split("|")]
            raw_fields = {}
            field_lines = {}
            if len(header) != 3 or not all(header):
                raise BuildError(f"line {number}: header needs 'id | type | group'")
            continue
        name, separator, value = line.partition(": ")
        if not header or name not in COLUMNS or not separator:
            raise BuildError(f"line {number}: cannot read {line[:40]!r}")
        if name in raw_fields:
            raise BuildError(f"line {number}: {header[0]} repeats {name}")
        raw_fields[name] = value
        field_lines[name] = number
    finish()
    ids = [rfi.rfi_id for rfi in rfis]
    if len(set(ids)) != len(ids):
        raise BuildError("duplicate rfi_id")
    return rfis


def _csv_bytes(header: list[str], rows: list[list[str]]) -> bytes:
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(header)
    writer.writerows(rows)
    return buffer.getvalue().encode("utf-8")


def _number(value: int | None) -> str:
    return "" if value is None else str(value)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def build(source: str) -> dict[str, bytes]:
    rfis = parse_source(source)
    files: dict[str, bytes] = {}
    files["heldout/input/rfis.csv"] = _csv_bytes(
        ["rfi_id", "subject", "question", "response"],
        [[r.rfi_id] + [r.columns[name].text for name in COLUMNS] for r in rfis],
    )
    cite_rows: list[list[str]] = []
    negative_rows: list[list[str]] = []
    for r in rfis:
        for name in COLUMNS:
            parsed = r.columns[name]
            for c in sorted(parsed.citations, key=lambda item: item.start):
                cite_rows.append(
                    [
                        r.rfi_id,
                        name,
                        str(c.start),
                        str(c.end),
                        _number(c.clause_start),
                        _number(c.clause_end),
                        c.key,
                        c.base_key,
                        c.scope,
                        "1" if c.inferred else "0",
                        c.catalog,
                        c.noise_class,
                    ]
                )
            for n in sorted(parsed.negatives, key=lambda item: item.start):
                negative_rows.append([r.rfi_id, name, str(n.start), str(n.end), n.kind])
    files["heldout/labels/citations.csv"] = _csv_bytes(
        [
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
        ],
        cite_rows,
    )
    files["heldout/labels/negatives.csv"] = _csv_bytes(
        ["rfi_id", "column", "start", "end", "kind"], negative_rows
    )
    files["heldout/labels/rfis.csv"] = _csv_bytes(
        ["rfi_id", "issue_type", "group_id", "template_id", "family"],
        [[r.rfi_id, r.issue_type, r.group_id, "", "written"] for r in rfis],
    )
    files["heldout/README.txt"] = README_TEXT.encode("utf-8")
    files["heldout/manifest.json"] = _manifest(rfis, files, source)
    return files


def _count(items: list[str]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in items:
        counts[item] = counts.get(item, 0) + 1
    return dict(sorted(counts.items()))


def _manifest(rfis: list[ParsedRfi], files: dict[str, bytes], source: str) -> bytes:
    cites = [c for r in rfis for p in r.columns.values() for c in p.citations]
    negatives = [n for r in rfis for p in r.columns.values() for n in p.negatives]
    in_scope = [c for c in cites if c.scope == "in"]
    groups: dict[str, list[str]] = {}
    for r in rfis:
        groups.setdefault(r.group_id, []).append(r.rfi_id)
    recurring = {name: ids for name, ids in groups.items() if len(ids) > 1}
    manifest = {
        "synthetic": True,
        "source": {
            "path": SOURCE_PATH,
            "sha256": sha256(source.encode("utf-8")),
        },
        "files": {name: sha256(data) for name, data in sorted(files.items())},
        "counts": {
            "rfis": len(rfis),
            "citations_in_scope": len(in_scope),
            "citations_out_of_scope": len(cites) - len(in_scope),
            "citations_per_body": _count([c.key.split(" ")[0] for c in in_scope]),
            "citations_inferred": len([c for c in in_scope if c.inferred]),
            "noise_classes": _count([c.noise_class for c in in_scope if c.noise_class]),
            "negatives": len(negatives),
            "negatives_per_kind": _count([n.kind for n in negatives]),
            "issue_types": _count([r.issue_type for r in rfis]),
            "recurring_groups": len(recurring),
        },
        "recurring_groups": dict(sorted(recurring.items())),
    }
    return (json.dumps(manifest, indent=2) + "\n").encode("utf-8")


def read_source(root: Path) -> str:
    data = (root / SOURCE_PATH).read_bytes()
    return data.decode("utf-8")


def check(root: Path) -> list[str]:
    source = read_source(root)
    problems: list[str] = []
    for name, data in build(source).items():
        path = root / name
        if not path.exists():
            problems.append(f"missing: {name}")
        elif path.read_bytes() != data:
            problems.append(f"differs: {name}")
    return problems


def write(root: Path) -> None:
    source = read_source(root)
    for name, data in build(source).items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)


def main(argv: list[str]) -> int:
    try:
        if argv == ["--check"]:
            problems = check(ROOT)
            for problem in problems:
                print(problem)
            if problems:
                print("heldout files are out of date: run scripts/build_heldout.py")
                return 1
            print("heldout files match the source")
            return 0
        if argv:
            print("usage: build_heldout.py [--check]")
            return 2
        write(ROOT)
    except BuildError as error:
        print(f"error: {error}")
        return 1
    except FileNotFoundError as error:
        print(f"error: cannot find {error.filename}")
        return 1
    except UnicodeDecodeError as error:
        print(f"error: the source is not valid UTF-8: {error.reason}")
        return 1
    print("heldout files written")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
