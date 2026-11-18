import re
from pathlib import Path

import pytest

from rfikit.notice import DISCLAIMER, LICENSE_LINE, OWNERS

SITE = Path(__file__).resolve().parent.parent / "site"
PAGES = ("index.html", "results.html")
CSP = (
    "default-src 'none'; script-src 'self' 'wasm-unsafe-eval' 'unsafe-eval'; "
    "connect-src 'self'; style-src 'self'; img-src 'self' data:; "
    "base-uri 'none'; form-action 'none'"
)


def plain(html: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", html))


@pytest.mark.parametrize("page", PAGES)
def test_footer_has_the_exact_notices(page: str) -> None:
    text = plain((SITE / page).read_text("utf-8"))
    assert DISCLAIMER in text
    assert LICENSE_LINE in text
    assert OWNERS in text


@pytest.mark.parametrize("page", PAGES)
def test_page_has_the_exact_csp_and_no_inline_code(page: str) -> None:
    html = (SITE / page).read_text("utf-8")
    assert f'content="{CSP}"' in html
    for tag in re.findall(r"<script[^>]*>", html):
        assert "src=" in tag
    assert "<style" not in html
    assert not re.search(r"\sstyle=|\son[a-z]+=", html)


def test_scripts_never_build_html_from_text() -> None:
    for path in SITE.glob("*.js"):
        code = path.read_text("utf-8")
        for banned in (
            "innerHTML",
            "outerHTML",
            "insertAdjacentHTML",
            "document.write",
        ):
            assert banned not in code, (path.name, banned)
        assert "eval(" not in code


def test_pages_name_no_other_host() -> None:
    hosts = set()
    for path in SITE.iterdir():
        if path.suffix in (".html", ".js", ".css"):
            hosts.update(re.findall(r"https?://([^/\"' )]+)", path.read_text("utf-8")))
    assert hosts <= {"github.com", "www.linkedin.com"}
