# 12. The in-browser demo

Status: Accepted

## Context

The spec asks for a static demo on GitHub Pages. Pasted RFI text may be real project text, so it must not leave the browser. Citation offsets in rfikit count code points, and JavaScript strings count UTF-16 units, so an emoji before a citation would shift every highlight by one.

## Decision

Python and offsets. The page runs rfikit in Pyodide 314.0.8. The module rfikit.demo is the only Python the page calls. find_citations returns plain dicts with offsets already converted to UTF-16 units, using one pass over the text (utf16_offsets). sample_text builds three RFIs from rfikit.synth for a seed. The page never converts offsets. Tests: unit and property tests for utf16_offsets and find_citations, and a browser test that pastes two emoji before a citation and checks the text node before the mark.

Highlights. The page builds the marked text with document.createTextNode and element nodes only, and the body name is written inside each mark in a span, so meaning does not depend on color. The key table and the results page use textContent too. No script builds HTML from text, and tests/test_site_files.py fails on innerHTML, outerHTML, insertAdjacentHTML, document.write and eval.

Pages and CSP. Two pages, index.html (paste mode) and results.html (measured.json as tables for the three sets, labeled measured on synthetic data). Both use the meta CSP from the spec and no inline script or style. A test compares the meta tag to the exact string.

Serving. scripts/build_site.py writes _site/ (the output folder must be named _site inside the repo). It fetches the Pyodide core archive from the official release into a gitignored cache, checks the archive against a pinned sha256 and pyodide.js against a pinned sha384 before anything is written, copies five files by exact path, and nothing downloaded is executed at build time. The rfikit wheel is built with SOURCE_DATE_EPOCH set and hatchling pinned, and the page unpacks it with unpackArchive, with no micropip. measured.json is copied from src/rfikit. This is the same pattern as the sibling ledgercheck demo.

CI. .github/workflows/pages.yml builds on pull requests without deploying and deploys only from main, with one concurrency group per ref. The Playwright test runs in its own browser job. A context route aborts and records any request to another host, and the last test fails if one was seen or if the console shows an error. The required check "ci" waits for both jobs.

Options considered:

- Convert offsets in JavaScript. Less Python, but the one place that is easy to get wrong would have no unit test.
- Use innerHTML with escaping. Shorter, but one missed escape is a script injection on a page that holds pasted text.
- Load Pyodide from a CDN. Smaller site, but pasted text could then share a page with third-party code.

## Consequences

The site is about 13.8 MB, mostly pyodide.asm.wasm and python_stdlib.zip. The first load takes a while. A meta CSP cannot set frame-ancestors, and Pages cannot send headers, so another site can frame the page. The page has no login and sets no cookies. The text limit is 200,000 characters. A Pyodide upgrade changes the version, URL, sha256 and sha384 in one file. Console error and overflow checks at 1366 and 390 pixels run in tests_browser. The axe accessibility check was run by hand, is not in this repo and is not in CI.
