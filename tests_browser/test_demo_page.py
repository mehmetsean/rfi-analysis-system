import json
import os
from collections.abc import Iterator
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import pytest

URL = os.environ.get("RFIKIT_DEMO_URL", "")
pytestmark = pytest.mark.skipif(not URL, reason="set RFIKIT_DEMO_URL to run")

ROOT = Path(__file__).resolve().parent.parent
MEASURED = json.loads((ROOT / "src" / "rfikit" / "measured.json").read_text("utf-8"))
LOAD_MS = 180_000
OVERFLOW = "document.documentElement.scrollWidth - document.documentElement.clientWidth"
EMOJI = "\U0001f600"
TEXT = "Please see IEEE 1547-2018 clause 4.2 and ASTM A36 for the bracket."


class Watch:
    def __init__(self) -> None:
        self.blocked: set[str] = set()
        self.errors: list[str] = []


@pytest.fixture(scope="module")
def watch() -> Watch:
    return Watch()


@pytest.fixture(scope="module")
def context(watch: Watch) -> Iterator[Any]:
    sync_api = pytest.importorskip("playwright.sync_api")
    here = urlparse(URL).netloc
    with sync_api.sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 1366, "height": 900})

        def guard(route: Any) -> None:
            parts = urlparse(route.request.url)
            if parts.scheme in ("http", "https") and parts.netloc != here:
                watch.blocked.add(parts.netloc)
                route.abort()
            else:
                route.continue_()

        ctx.route("**/*", guard)
        ctx.on("websocket", lambda ws: watch.blocked.add("websocket " + ws.url))
        yield ctx
        browser.close()


def watched(page: Any, watch: Watch) -> None:
    page.on(
        "console", lambda m: watch.errors.append(m.text) if m.type == "error" else 0
    )
    page.on("pageerror", lambda e: watch.errors.append(str(e)))


@pytest.fixture(scope="module")
def page(context: Any, watch: Watch) -> Any:
    pg = context.new_page()
    watched(pg, watch)
    pg.goto(URL)
    pg.wait_for_function("!document.getElementById('run').disabled", timeout=LOAD_MS)
    return pg


def run(page: Any, text: str) -> None:
    page.fill("#text", text)
    page.click("#run")
    page.wait_for_selector("#results:not([hidden])")


def marks(page: Any) -> list[dict[str, Any]]:
    return page.evaluate(
        """() => [...document.querySelectorAll('#marked mark')].map(m => ({
          cited: m.firstChild.nodeValue,
          tag: m.lastChild.textContent,
          nodes: m.childNodes.length,
          before: m.previousSibling ? m.previousSibling.nodeValue : null,
        }))"""
    )


def test_paste_highlights_and_lists_keys(page: Any) -> None:
    run(page, TEXT)
    found = marks(page)
    assert [m["cited"] for m in found] == ["IEEE 1547-2018", "ASTM A36"]
    assert [m["tag"] for m in found] == ["IEEE", "ASTM"]
    assert all(m["nodes"] == 2 for m in found)
    assert page.locator("#keys tbody tr").count() == 2
    first = page.locator("#keys tbody tr").first.locator("td").all_inner_texts()
    assert first[1:] == [
        "IEEE 1547-2018",
        "IEEE 1547-2018 Clause 4.2",
        "IEEE 1547",
        "IEEE",
        "clause 4.2",
    ]
    assert "2 citations found" in page.inner_text("#count")


def test_marked_text_keeps_the_pasted_text(page: Any) -> None:
    run(page, TEXT)
    plain = page.evaluate(
        """() => {
          const out = [];
          for (const n of document.getElementById('marked').childNodes) {
            out.push(n.nodeType === 3 ? n.nodeValue : n.firstChild.nodeValue);
          }
          return out.join('');
        }"""
    )
    assert plain == TEXT


def test_astral_character_before_a_citation(page: Any) -> None:
    text = f"Note {EMOJI}{EMOJI} then IEEE 1547-2018 and {EMOJI} NEMA MG 1 here."
    run(page, text)
    found = marks(page)
    assert [m["cited"] for m in found] == ["IEEE 1547-2018", "NEMA MG 1"]
    assert found[0]["before"] == f"Note {EMOJI}{EMOJI} then "
    assert found[1]["before"] == f" and {EMOJI} "


def test_marks_and_keys_are_not_translated(page: Any) -> None:
    run(page, TEXT)
    assert page.eval_on_selector("mark.cite", "e => e.translate") is False
    assert page.eval_on_selector("#keys .scroll td", "e => e.translate") is False


def test_html_in_the_text_stays_text(page: Any) -> None:
    run(page, "<b>bold</b> <img src=x onerror=alert(1)> IEEE 1547-2018")
    assert page.locator("#marked b, #marked img").count() == 0
    assert [m["cited"] for m in marks(page)] == ["IEEE 1547-2018"]


def test_one_citation_is_singular_and_counts_code_points(page: Any) -> None:
    run(page, f"{EMOJI} ASTM A36")
    assert page.inner_text("#count") == "1 citation found in 10 characters."


def test_text_without_citations(page: Any) -> None:
    run(page, "Nothing to see here.")
    assert marks(page) == []
    assert "No citations found" in page.inner_text("#keys")
    assert "0 citations found" in page.inner_text("#count")


def test_sample_by_seed(page: Any) -> None:
    page.fill("#seed", "42")
    page.click("#sample")
    page.wait_for_selector("#results:not([hidden])")
    first = page.input_value("#text")
    assert first and "seed 42" in page.inner_text("#status")
    count = len(marks(page))
    assert count > 0
    assert page.locator("#keys tbody tr").count() == count
    page.fill("#seed", "43")
    page.click("#sample")
    assert page.input_value("#text") != first
    page.fill("#seed", "42")
    page.click("#sample")
    assert page.input_value("#text") == first


@pytest.mark.parametrize("bad", ["-5", "", "1.5", "1000000"])
def test_bad_seed_gives_a_message_at_the_field(page: Any, bad: str) -> None:
    page.fill("#seed", bad)
    page.click("#sample")
    assert page.is_visible("#seed-error")
    assert "whole number" in page.inner_text("#seed-error")
    assert "try again" in page.inner_text("#seed-error")
    assert page.get_attribute("#seed", "aria-invalid") == "true"
    assert page.get_attribute("#seed", "aria-describedby") == "seed-error"
    page.fill("#seed", "42")
    page.click("#sample")
    assert page.is_hidden("#seed-error")
    assert page.get_attribute("#seed", "aria-invalid") == "false"


def test_clear_hides_the_results(page: Any) -> None:
    run(page, TEXT)
    page.click("#clear")
    assert page.is_hidden("#results")
    assert page.input_value("#text") == ""


def test_keyboard_path(page: Any) -> None:
    page.click("#clear")
    page.focus("#text")
    page.keyboard.type("Use ASTM A36 here.")
    page.keyboard.press("Tab")
    assert page.evaluate("document.activeElement.id") == "run"
    page.keyboard.press("Enter")
    page.wait_for_selector("#results:not([hidden])")
    assert [m["cited"] for m in marks(page)] == ["ASTM A36"]
    page.keyboard.press("Tab")
    assert page.evaluate("document.activeElement.id") == "clear"
    page.keyboard.press("Tab")
    assert page.evaluate("document.activeElement.id") == "seed"
    page.keyboard.press("Tab")
    assert page.evaluate("document.activeElement.id") == "sample"


def test_every_control_has_a_label(page: Any) -> None:
    missing = page.evaluate(
        """() => [...document.querySelectorAll('input, textarea, select, button')]
          .filter(c => !(c.labels && c.labels.length) && !c.textContent.trim())
          .map(c => c.id)"""
    )
    assert missing == []


def test_no_overflow_on_the_page(page: Any) -> None:
    run(page, ("IEEE 1547-2018 " + "x" * 200 + " ") * 3)
    for width in (1366, 390):
        page.set_viewport_size({"width": width, "height": 800})
        extra = page.evaluate(OVERFLOW)
        assert extra <= 0
    page.set_viewport_size({"width": 1366, "height": 900})


def test_results_page_shows_measured_tables(context: Any, watch: Watch) -> None:
    pg = context.new_page()
    watched(pg, watch)
    pg.goto(URL + "results.html")
    pg.wait_for_selector("#sets table")
    heads = pg.locator("#sets h2").all_inner_texts()
    assert len(heads) == 3
    assert all("measured on synthetic data" in h for h in heads)
    assert pg.locator("#sets table").count() == 9
    cell = pg.locator("#sets table").first.locator("tbody tr").nth(2)
    got = cell.locator("td").all_inner_texts()
    want = MEASURED["full"]["sets"]["A"]["methods"]["rfikit"]["levels"]["full"]
    assert got == [
        "rfikit",
        "full key",
        f"{want['precision']:.3f}",
        f"{want['recall']:.3f}",
        f"{want['f1']:.3f}",
    ]
    body_rows = pg.locator("#sets table").nth(1).locator("tbody tr").count()
    assert body_rows == 6
    for width in (1366, 390):
        pg.set_viewport_size({"width": width, "height": 800})
        extra = pg.evaluate(OVERFLOW)
        assert extra <= 0
    scrolls = pg.evaluate(
        "[...document.querySelectorAll('.scroll')]"
        ".some(s => s.scrollWidth > s.clientWidth)"
    )
    assert scrolls
    pg.close()


@pytest.mark.parametrize(
    ("given", "want"),
    [
        ("Traceback (most recent call last):\nValueError: bad input.", "bad input"),
        ("ValueError: key: value", "key: value"),
        ("boom", "boom"),
        ("done..", "done"),
        ("", "unknown error"),
    ],
)
def test_plain_error_cleans_messages(context: Any, given: str, want: str) -> None:
    pg = context.new_page()
    pg.goto(URL + "results.html")
    got = pg.evaluate("m => [plainError(new Error(m)), plainError(m)]", given)
    assert got == [want, want]
    pg.close()


def test_results_page_load_error_is_plain(context: Any) -> None:
    pg = context.new_page()
    pg.route("**/measured.json", lambda r: r.fulfill(status=404, body="no"))
    pg.goto(URL + "results.html")
    pg.wait_for_function(
        "document.getElementById('status').textContent.includes('Could not')"
    )
    text = pg.inner_text("#status")
    assert text == (
        "Could not load the results: measured.json is missing from this site."
        " Reload the page to try again."
    )
    pg.close()


def test_footer_notices_are_on_both_pages(page: Any, context: Any) -> None:
    other = context.new_page()
    other.goto(URL + "results.html")
    for pg in (page, other):
        text = pg.inner_text("footer")
        assert "Decision support only" in text
        assert "All rights reserved." in text
    other.close()


def test_no_request_left_the_origin_and_no_errors(watch: Watch, page: Any) -> None:
    assert watch.blocked == set()
    assert watch.errors == []
