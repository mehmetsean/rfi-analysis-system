import html as html_lib
import re
from html.parser import HTMLParser
from pathlib import Path

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from rfikit.analyze import analyze
from rfikit.io import InputError
from rfikit.notice import DISCLAIMER, LICENSE_LINE, OWNERS
from rfikit.report import (
    RATES_TITLE,
    analyze_to,
    csv_batches,
    load_measured,
    md_cell,
    plain_cell,
    rate_rows,
    render_html,
    render_markdown,
    render_readme,
    short_cell,
    write_analysis,
)
from rfikit.types import Rfi

DOC = load_measured()
ROWS = [
    Rfi("R1", "IEEE 80 and IEEE 80-2013", "ASTM A123", "NEMA TC 2"),
    Rfi("R2", "IEEE 1547", "ASTM A123", ""),
    Rfi("R3", "nothing", "", ""),
]
ALLOWED_TAGS = {
    "html",
    "head",
    "meta",
    "title",
    "style",
    "body",
    "main",
    "h1",
    "h2",
    "p",
    "div",
    "table",
    "thead",
    "tbody",
    "tr",
    "th",
    "td",
}
ALLOWED_ATTRS = {
    "lang",
    "charset",
    "http-equiv",
    "content",
    "name",
    "class",
    "tabindex",
    "role",
    "aria-label",
    "scope",
}


def test_markdown_tables() -> None:
    text = render_markdown(analyze(ROWS), DOC)
    assert "| RFIs read | 3 |" in text
    assert "| Citations found | 6 |" in text
    assert "| IEEE 80 | 2 |" in text
    assert "| ASTM A123 | 2 |" in text
    assert "| IEEE | 3 |" in text
    assert "| 0 | 1 |" in text
    assert "| 4 | 1 |" in text
    assert "| R1 | 4 |" in text
    assert text.index("| ASTM A123 | 2 |") < text.index("| IEEE 80 | 2 |")


def test_markdown_rates_and_na() -> None:
    text = render_markdown(analyze(ROWS), DOC)
    assert RATES_TITLE == "Extraction rates, measured on synthetic data"
    assert "## " + RATES_TITLE in text
    for name in ("Family A, report seeds", "Family B, report seeds", "Written set"):
        assert name in text
    naive_full = [line for line in text.splitlines() if "| naive baseline" in line]
    assert any("| full key | n/a | n/a | n/a |" in line for line in naive_full)
    assert any("| strict span |" in line and "n/a" not in line for line in naive_full)
    rfikit = [
        line for line in text.splitlines() if line.startswith("| rfikit | Family A")
    ]
    assert len(rfikit) == 5


def test_rates_missing_set_and_level() -> None:
    doc = {"data": "x", "full": {"sets": {"A": {"methods": {"rfikit": {}}}}}}
    rows = rate_rows(doc)
    assert len(rows) == 3 * 3 * 5
    assert all(row[3:] == ("n/a", "n/a", "n/a") for row in rows)


def test_rates_null_value() -> None:
    levels = {"strict": {"precision": None, "recall": 0.5, "f1": 1.0}}
    doc = {"full": {"sets": {"A": {"methods": {"rfikit": {"levels": levels}}}}}}
    row = [
        r
        for r in rate_rows(doc)
        if r[:3] == ("rfikit", "Family A, report seeds", "strict span")
    ]
    assert row == [
        ("rfikit", "Family A, report seeds", "strict span", "n/a", "0.500", "1.000")
    ]


def test_empty_input_text() -> None:
    result = analyze([])
    text = render_markdown(result, DOC)
    assert "| RFIs read | 0 |" in text
    assert "No citations found." in text
    page = render_html(result, DOC)
    assert "No citations found." in page
    assert "<td>0</td>" in page


def test_no_citations_but_rfis() -> None:
    text = render_markdown(analyze([Rfi("A", "x", "y", "")]), DOC)
    assert "| 0 | 1 |" in text
    assert "No citations found." in text


def test_notice_and_disclaimer_everywhere() -> None:
    result = analyze(ROWS)
    for text in (render_markdown(result, DOC), render_readme(result)):
        assert DISCLAIMER in text
    page = render_html(result, DOC)
    assert html_lib.escape(DISCLAIMER, quote=True) in page
    assert LICENSE_LINE in render_readme(result)
    assert LICENSE_LINE in html_lib.unescape(page)


def test_synthetic_marker() -> None:
    plain = analyze(ROWS)
    synth = analyze(ROWS, synthetic=True)
    assert "synthetic data" not in render_readme(plain).split("License")[0]
    assert render_readme(synth).startswith("Synthetic data.")
    assert "The input is synthetic data." in render_markdown(synth, DOC)
    assert "The input is synthetic data." in render_html(synth, DOC)
    assert "The input is synthetic data." not in render_markdown(plain, DOC)


def test_readme_lists_files() -> None:
    text = render_readme(analyze(ROWS))
    for name in ("citations.csv", "analysis.md", "analysis.html"):
        assert name in text


def test_md_cell_escapes() -> None:
    assert md_cell("a|b") == "a\\|b"
    assert md_cell("a\\b") == "a\\\\b"
    assert md_cell("`x`") == "\\`x\\`"
    assert md_cell("<b>") == "\\<b\\>"
    assert md_cell("[a](b)") == "\\[a\\](b)"
    assert md_cell("a\nb\r\nc d") == "a b c d"
    assert md_cell("&lt;") == "\\&lt;"


EVIL = "<script>alert(1)</script>|`[x](http://e)`\n=cmd"


def test_markdown_injection() -> None:
    text = render_markdown(analyze([Rfi(EVIL, "IEEE 80", "", "")]), DOC)
    assert "<script>" not in text
    assert "\n=cmd" not in text
    row = [line for line in text.splitlines() if "script" in line]
    assert len(row) == 1
    assert len(re.split(r"(?<!\\)\|", row[0])) == 4
    assert "[x](" not in row[0]


def test_html_injection() -> None:
    page = render_html(analyze([Rfi(EVIL, "IEEE 80", "", "")]), DOC)
    assert "<script" not in page
    assert "&lt;script&gt;" in page
    assert "&#x27;" in page or "&quot;" in page or "&lt;" in page


def test_html_is_static() -> None:
    page = render_html(analyze(ROWS), DOC)
    assert "Content-Security-Policy" in page
    plain = html_lib.unescape(page)
    assert "default-src 'none'" in plain
    assert "style-src 'unsafe-inline'" in plain
    assert "<script" not in page
    assert not re.search(r"\son\w+\s*=", page)
    assert "http://" not in page and "src=" not in page and "href=" not in page


class Tags(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.tags: set[str] = set()
        self.attrs: set[str] = set()

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.tags.add(tag)
        self.attrs.update(name for name, _ in attrs)


def parsed(page: str) -> Tags:
    parser = Tags()
    parser.feed(page)
    parser.close()
    return parser


TEXTS = st.text(max_size=30) | st.sampled_from([EVIL, "<b>", "'\"&", "a|b", "=1+1"])
PIECES = st.sampled_from(["IEEE 80", "ASTM A123", "NESC Rule 232", " ", "x"])


@settings(max_examples=60)
@given(st.lists(st.tuples(TEXTS, TEXTS, PIECES), max_size=6))
def test_input_cannot_add_markup(items: list[tuple[str, str, str]]) -> None:
    rows = [Rfi(f"{a}{i}", f"{p} {b}", b, "") for i, (a, b, p) in enumerate(items)]
    result = analyze(rows)
    found = parsed(render_html(result, DOC))
    assert found.tags <= ALLOWED_TAGS
    assert found.attrs <= ALLOWED_ATTRS
    text = render_markdown(result, DOC)
    for line in text.splitlines():
        if line.startswith("|"):
            cells = re.split(r"(?<!\\)\|", line)
            assert cells[0] == "" and cells[-1] == ""
            assert len(cells) in (4, 8)
            assert not re.search(r"(?<!\\)<", line)


def test_write_analysis_files(tmp_path: Path) -> None:
    analyze_to(tmp_path, ROWS)
    names = sorted(p.name for p in tmp_path.iterdir())
    assert names == ["README.txt", "analysis.html", "analysis.md", "citations.csv"]
    lines = (tmp_path / "citations.csv").read_text(encoding="utf-8").splitlines()
    assert lines[0].startswith("rfi_id,column,start,end,text,key,base_key,body")
    assert len(lines) == 7


def test_write_analysis_escapes_formula_cells(tmp_path: Path) -> None:
    analyze_to(tmp_path, [Rfi("=1+1", "IEEE 80", "", "")])
    lines = (tmp_path / "citations.csv").read_text(encoding="utf-8").splitlines()
    assert lines[1].startswith("'=1+1,subject,")


def test_write_analysis_is_byte_stable(tmp_path: Path) -> None:
    first = tmp_path / "a"
    second = tmp_path / "b"
    first.mkdir()
    second.mkdir()
    analyze_to(first, ROWS)
    analyze_to(second, ROWS)
    for path in first.iterdir():
        assert path.read_bytes() == (second / path.name).read_bytes()


def test_write_analysis_refuses_protected_file(tmp_path: Path) -> None:
    source = tmp_path / "citations.csv"
    source.write_text("keep", encoding="utf-8")
    with pytest.raises(InputError, match="same file"):
        analyze_to(tmp_path, ROWS, protected=[source])
    assert source.read_text(encoding="utf-8") == "keep"


def test_write_analysis_refuses_symlink_target(tmp_path: Path) -> None:
    other = tmp_path / "other.txt"
    other.write_text("keep", encoding="utf-8")
    out = tmp_path / "out"
    out.mkdir()
    (out / "analysis.md").symlink_to(other)
    with pytest.raises(InputError, match="symbolic link"):
        analyze_to(out, ROWS)
    assert other.read_text(encoding="utf-8") == "keep"


def test_write_analysis_refuses_directory_target(tmp_path: Path) -> None:
    (tmp_path / "README.txt").mkdir()
    with pytest.raises(InputError, match="not a regular file"):
        analyze_to(tmp_path, ROWS)


def test_write_analysis_missing_folder(tmp_path: Path) -> None:
    with pytest.raises(InputError, match="cannot be written"):
        analyze_to(tmp_path / "missing", ROWS)


def test_write_analysis_replaces_own_files(tmp_path: Path) -> None:
    (tmp_path / "analysis.md").write_text("old", encoding="utf-8")
    analyze_to(tmp_path, ROWS)
    assert "# rfikit analysis" in (tmp_path / "analysis.md").read_text(encoding="utf-8")


def test_csv_batches_split_rows(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("rfikit.report.BATCH", 2)
    chunks = list(csv_batches([["a"], ["b"], ["c"]]))
    assert chunks == ["a\nb\n", "c\n"]


def test_write_analysis_writes_the_three_report_files(tmp_path: Path) -> None:
    write_analysis(tmp_path, analyze(ROWS))
    assert sorted(p.name for p in tmp_path.iterdir()) == [
        "README.txt",
        "analysis.html",
        "analysis.md",
    ]


def test_plain_cell_replaces_controls() -> None:
    assert plain_cell("a\x1b[31mb\x07c") == "a\\x1b[31mb\\x07c"
    assert plain_cell("x\x7fy\x85z\x9f") == "x\\x7fy\\x85z\\x9f"
    assert plain_cell("tab\there\r\nok \u202e") == "tab\there\r\nok \u202e"


def test_csv_cells_have_no_raw_controls(tmp_path: Path) -> None:
    analyze_to(tmp_path, [Rfi("A\x1b[2J\x07", "IEEE 80", "", "")])
    raw = (tmp_path / "citations.csv").read_bytes()
    assert b"\x1b" not in raw and b"\x07" not in raw
    assert b"A\\x1b[2J\\x07" in raw


def test_short_cell() -> None:
    assert short_cell("R0044") == "R0044"
    assert short_cell("x" * 40) == "x" * 40
    assert short_cell("x" * 41) == "x" * 40 + "..."
    assert short_cell("a\x1bb\u202ec\nd\u2028e\u200bf") == "a b c d e f"


def test_rfi_id_cells_are_plain() -> None:
    result = analyze([Rfi("rfi_id_1\u202e", "IEEE 80", "", "")])
    text = render_markdown(result, DOC)
    assert "| RFI id | Citations |" in text
    assert "| rfi\\_id\\_1  | 1 |" in text
    assert "'rfi" not in text
    assert "<td>rfi_id_1 </td>" in render_html(result, DOC)


def test_bare_nesc_is_labeled() -> None:
    result = analyze([Rfi("A", "per 2002 NESC", "NESC Rule 232", "")])
    assert ("NESC", 1) in result.key_counts
    for text in (render_markdown(result, DOC), render_html(result, DOC)):
        assert "NESC (no rule given)" in text
        assert "no rule, table or section" in text
    assert "NESC (no rule given)" not in render_markdown(analyze(ROWS), DOC)


def test_bare_nesc_key_stays_in_csv(tmp_path: Path) -> None:
    analyze_to(tmp_path, [Rfi("A", "per 2002 NESC", "", "")])
    row = (tmp_path / "citations.csv").read_text(encoding="utf-8").splitlines()[1]
    assert ",NESC 2002,NESC," in row


def test_md_cell_blocks_autolinks() -> None:
    assert md_cell("x www.evil.com") == "x www\\.evil.com"
    assert md_cell("x http://evil.com") == "x http\\://evil.com"
    assert md_cell("HTTPS://a.b ftp://c.d") == "HTTPS\\://a.b ftp\\://c.d"
    assert md_cell("awww.x") == "awww.x"


def test_md_cell_tilde() -> None:
    assert md_cell("~~x~~") == "\\~\\~x\\~\\~"


def test_rate_ignores_booleans() -> None:
    levels = {"strict": {"precision": True, "recall": 0.5, "f1": False}}
    doc = {"full": {"sets": {"A": {"methods": {"rfikit": {"levels": levels}}}}}}
    row = [r for r in rate_rows(doc) if r[:3][2] == "strict span" and r[0] == "rfikit"]
    assert row[0][3:] == ("n/a", "0.500", "n/a")


def test_short_cell_line_separators() -> None:
    assert short_cell("a\u2029b") == "a b"


def test_plain_cell_unit_separator() -> None:
    assert plain_cell("a\x1fb") == "a\\x1fb"


def test_md_cell_line_separator() -> None:
    assert md_cell("a\u2029b") == "a b"


def test_md_cell_uppercase_www() -> None:
    assert md_cell("WWW.example.com") == "WWW\\.example.com"


def test_nesc_note_text_and_condition(monkeypatch: pytest.MonkeyPatch) -> None:
    rows = [Rfi("A", "IEEE 80 and 2002 NESC", "IEEE 80", "")]
    result = analyze(rows)
    note = (
        "NESC (no rule given) counts citations to the NESC, also written as ANSI "
        "C2 or IEEE C2, that give no rule, table or section, such as an edition "
        "alone. It is not a count of one rule."
    )
    assert note in render_markdown(result, DOC)
    assert note in render_html(result, DOC)
    monkeypatch.setattr("rfikit.report.TOP_KEYS", 1)
    assert note not in render_markdown(result, DOC)
    assert "NESC (no rule given)" not in render_html(result, DOC)


def test_markdown_notice_lines_are_not_escaped() -> None:
    text = render_markdown(analyze(ROWS), DOC)
    assert LICENSE_LINE in text
    assert DISCLAIMER in text
    assert OWNERS in text


def test_readme_blank_line_before_owners() -> None:
    assert f"{DISCLAIMER}\n\n{OWNERS}" in render_readme(analyze(ROWS))
