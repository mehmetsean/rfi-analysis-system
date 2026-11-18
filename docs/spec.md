# rfikit spec (v0.1, with the v0.2 and v0.3 plan)

Repository: rfi-analysis-system. Package, import and CLI name: rfikit. This rebuild replaces the 2025 prototype script (see "The prototype").

## Problem
A request for information (RFI) is a written question from a contractor to the design team on a construction or utility project. Many RFIs turn on a standard: which edition of IEEE C57.12.00 applies, whether NESC Rule 232 covers a crossing, whether an ASTM A123/A123M coating meets the spec. A team that wants to know which standards come up most, which RFIs repeat an earlier question and what kind of issue each one raises reads the log line by line. Project platforms offer RFI summaries and search inside their own cloud; we found no tool, open or commercial, that publishes the accuracy of its standard citation extraction, and none that runs on an exported log without sending the text out.
rfikit reads an RFI export on the user's machine or in a static browser page. It finds standard citations and normalizes each to a designation key, assigns an issue type with a stated reason, and groups recurring questions. Each task ships with precision and recall measured on labeled synthetic data next to a simple baseline, and the scripts and seeds to rerun every number are in the repo.

## User and buyer
- Document control and engineering teams at EPC firms, utilities, owner's engineers and construction managers who export RFI logs to CSV and want citation counts, repeat questions and issue types without uploading project text.
- Data and analytics people who want a tested example of span extraction, text classification and near-duplicate grouping with an honest evaluation.
- Money path: a paid commercial license per company, paid setup (column map, aliases, issue types and keyword rules tuned on a client's own export, run on the client's machine) and paid support.

## MVP (v0.1)
Python 3.11+, standard library only at runtime, so the same wheel runs in Pyodide with no extra packages. CLI:
`rfikit extract notes.txt` (citations as CSV), `rfikit analyze rfis.csv --out results/` (columns rfi_id, subject, question, optional response; other names through a JSON column map), `rfikit generate --seed 42 --n 600 --out data/`, `rfikit evaluate data/ --written heldout/`.

1. Citation extraction, the core. An anchor scan finds body tokens; a grammar per body reads the designation in a bounded window after the anchor. Each citation has a span (half-open character offsets into the original field), its text, a Designation (body, co_bodies, doc_type, number, part, year, suffix, clause), a full key and a base key (body, number, part; for NESC, whose number is always C2, the rule or table). Only designations and clause numbers are output, never titles or standard text.

| Body | Anchor forms | Designation after the anchor | Key example | Hard negatives (not citations) |
|---|---|---|---|---|
| IEEE | IEEE, IEEE Std, ANSI/IEEE | optional C, number with dotted levels (C57.12.00, 1547.1, 80), amendment letter, -YYYY | IEEE C57.12.00-2015 | IEEE Transactions, RFI-1547, 1547 kVA |
| NESC | NESC, IEEE C2, ANSI C2; bare Rule or Table only when the RFI cites NESC elsewhere | edition (2017 NESC, NESC-2017, C2-2017); Rule 232B1a, Table 232-1, Section 9 | NESC 2017 Rule 232B1 | Rule 12 of the contract, Room 232, sheet E-232-1 |
| IEC | IEC, IEC TS, IEC TR, IEC/IEEE | five-digit number, part levels (61850-7-4), :YYYY, +AMD1:YYYY | IEC 60076-1:2011 | IP65 alone, drawing 60076-1 |
| ANSI | ANSI not joined to another body | letter and dotted number (C84.1, C12.20, Z535.4), -YYYY | ANSI C84.1-2020 | ANSI 61 gray, ANSI Class 150, ANSI D size sheet |
| ASTM | ASTM | letter A to G and number, metric twin (/A123M), -YY, revision letter, (reapproval year), e1 | ASTM A123/A123M-17 | A36 without ASTM, part A123-4567 |
| NEMA | NEMA, ANSI/NEMA | letters and number (TC 2, MG 1, WD 6) or three digits (250), -YYYY | NEMA TC 2-2020 | NEMA 4X, NEMA 3R, NEMA 5-20R, NEMA Size 2, NEMA Premium |

- Joint prefixes: the first developing body written is the body; ANSI and any other bodies go to co_bodies ("ANSI/IEEE C37.2" is IEEE C37.2). Years are kept as written (ASTM uses two digits).
- Clauses attach when clause, section, sec., para, table, figure, annex or rule plus an id follows within 40 characters, or "Section 5.3 of IEEE 80" puts it before. Section and para become clause.
- List continuation: in "IEEE C57.12.00, C57.12.90 and C57.91" the later numbers inherit the body when they fit its grammar. Bare NESC rules and list items are marked inferred.
- Offset-preserving cleanup: a one-to-one character map turns Unicode dashes and no-break spaces into ASCII, so spans in the cleaned text are spans in the original. A line break inside a designation reads as a space, or is joined after "." or "-". Missing or extra spaces ("IEC60076-1", "ASTM A 123") and any letter case are accepted. Misspelled bodies ("IEE 1547") and letter O for zero are not repaired in v0.1 and are measured as misses by noise class.
- Other bodies (NFPA, UL, ASME, ISA, TIA, CSA, EN) are not extracted. Their labels are left out of scoring both ways and counted on their own line.

2. Issue type, one label per RFI from subject and question only (the response does not exist at triage time): design_clarification, missing_information, document_conflict, substitution_request, field_condition, standard_applicability. Methods: majority class (baseline); keyword rules (ordered phrase lists written for this repo, the reason names the phrase that fired, no match is an abstention scored as wrong and counted); multinomial naive Bayes written in the standard library (unigrams and bigrams, Laplace smoothing, citation spans replaced by a body token such as cite_ieee, numbers masked, top weighted tokens as the reason). The trained model ships as JSON, so the demo never trains.
3. Recurring questions. TF-IDF on subject and question (sublinear tf, citations replaced by their base key token, so "IEEE Std C57.12.00-2015" and "IEEE C57.12.00" match), cosine similarity, pairs at or above a threshold t joined by union-find. Each group lists its shared terms and shared citations.
4. Synthetic labeled RFIs in rfikit.synth: seeded random.Random, byte-identical files per seed and version, synthbiz output conventions (manifest.json with sha256 per file and "synthetic": true, README.txt in every folder, labels kept apart from inputs). Projects are codes (P-0412), disciplines generic (substation, distribution line, solar plant, commercial building), people role ids (CONTRACTOR_PM). No real company, facility, project or person, and nothing from any employer.
- Designations come from a catalog of real designation and clause numbers written for this repo (identifiers only) and from invented numbers that fit each grammar; labels mark which, so recall on invented numbers shows the grammar does not memorize the catalog. Templates never state what a standard requires.
- Hard negatives labeled by kind: the table's list plus part, drawing, room and RFI numbers, dates, kVA ratings and spec section numbers (26 05 26). Noise labeled by class: line breaks inside designations, spacing, case, Unicode dashes, misspelled bodies, list continuations.
- Template families per issue type with slot synonyms, clause order changes, optional greetings and responses. Families split into A (seen) and B (held out, about a quarter per type, committed on its own before any tuning). A recurring question is k paraphrases of one seed question under one group_id.
- Labels come from the generator's record of where it inserted each item, never from running the extractor.
5. Written held-out set in heldout/: about 80 RFIs written one by one for this repo, not by the generator, with at least 150 in-scope citations (15 or more per body), 40 hard negatives and 12 recurring groups; marked synthetic data. Labeled per docs/annotation_guide.md and committed with its sha256 before the extractor and rules are tuned, which the git history shows; later label fixes go to heldout/CHANGES.md.

`analyze` writes citations.csv, rfis.csv (issue type, method, reason, group_id), groups.csv, analysis.md and analysis.html (top base keys, issue type counts, largest groups, measured rates labeled "measured on synthetic data") and README.txt with the notice and disclaimer.

## Design
Constraints: runs in Pyodide, no network calls, methods never see labels, extraction linear in text length on hostile input, grouping past all-pairs cost without losing pairs above t.
Options. Extraction: per-body regexes over the whole text (the prototype: no spans, no normalization, "Rule 232" matched anywhere; kept as a baseline); a learned sequence tagger (needs real labeled text, which is not public, and would only learn the generator's grammar); chosen: anchor scan plus per-body grammar with no catalog lookup, so unseen standards are found. Classification: rules and naive Bayes now (closed-form training, inspectable weights); logistic regression and a local model later behind the same Classifier protocol. Grouping: all-pairs cosine is O(N^2); MinHash LSH is approximate and needs tuning; chosen: exact prefix filtering. Tokens are ordered rarest first and vectors have unit length. Each vector's suffix of common tokens grows while its L2 norm stays under t; only prefixes are indexed and whole vectors probe. A pair with no shared token in y's prefix has cosine <= ||suffix(y)|| x ||x|| < t, so the blocked result equals the all-pairs result above t. Union-find is single linkage, which can chain; the report prints the largest group.
Modules: types (frozen dataclasses), textnorm (character map, tokenizer), cite, classify, group, synth, io (CSV and text, column map, BOM, row and field caps), evaluate (the only module that reads labels), report (CSV, Markdown, HTML; cells starting with =, +, - or @ are escaped), analyze, cli. cite depends only on types and textnorm, so it can ship alone later; cite, classify and group import neither synth nor evaluate.
```python
def extract(text: str, field: str = "text", context: CiteContext | None = None) -> list[Citation]: ...
def extract_rfi(rfi: Rfi) -> list[Citation]: ...  # NESC context shared across fields
def parse_designation(raw: str) -> Designation | None: ...
class Classifier(Protocol):
    def predict(self, rfi: Rfi) -> Prediction: ...  # label, method, reason
def train_naive_bayes(rfis: Sequence[Rfi], labels: Sequence[str], alpha: float) -> NaiveBayes: ...
def group_rfis(rfis: Sequence[Rfi], threshold: float, budget: int) -> GroupResult: ...  # groups, candidates, compares
def generate(seed: int, n: int, params: GenParams | None = None) -> Corpus: ...
def read_rfis(path: Path, column_map: ColumnMap | None = None) -> list[Rfi]: ...
def evaluate(data: Path, written: Path | None, plan: EvalPlan) -> EvalReport: ...
def write_analysis(out: Path, result: AnalysisResult) -> None: ...
```
Data model: Rfi(rfi_id, subject, question, response); Citation(field, start, end, text, designation, inferred); Designation with key() and base_key(); Prediction(rfi_id, label, method, reason); Group(group_id, rfi_ids, terms, citations). Label files: labels/citations.csv (rfi_id, field, start, end, key, base_key, catalog, noise_class), labels/negatives.csv (rfi_id, field, start, end, kind), labels/rfis.csv (rfi_id, issue_type, group_id, family, split).
Complexity (n characters, a anchors, window w = 96, L tokens per RFI, K phrases, T tokens, V vocabulary, C classes, N RFIs, p candidate pairs, S seeds, B draws): extraction O(n + a x w) = O(n), bounded quantifiers only, so no regex backtracking blowup; NESC context one more O(n) pass. Rules O(L x K). Naive Bayes training O(T + V x C), prediction O(L x C). Grouping: TF-IDF O(T), prefixes O(T log T), p is the sum of prefix posting lengths over probes, O(N^2) in the worst case (every RFI shares rare tokens), so a budget on p stops the run with a clear message; each compare O(min(|x|, |y|)); union-find O(p alpha(N)). Scoring: span matching is a two-pointer sweep over sorted non-overlapping spans, O(g + q) per field for g gold and q predicted spans; pairwise grouping counts come from a contingency table in O(N), no pair list; bootstrap O(B x S).
Benchmark: benchmarks/bench.py writes docs/benchmark.md: extraction precision, recall and characters per second for a naive baseline (body token plus the next token), the prototype regexes and rfikit; grouping time, p and compares for all-pairs and prefix filtering at N = 1,000, 5,000 and 20,000, asserting both return the same pairs at or above t. CI runs a quick form with the assertion and no time limits.

## Evaluation design
- Seeds: train 1 to 5 (naive Bayes), tune 6 to 10 (rule phrases, alpha, t), report 101 to 130, 600 RFIs each. Every number is shown on three sets: in-family (split A, report seeds), out-of-family (split B, report seeds) and the written set. Templated text inflates scores, so the gap between the three is a result the README prints.
- Extraction: precision, recall and F1 at four levels: strict span (same field and offsets), overlap span (one-to-one by the sweep), full key (multiset of keys per RFI) and base key. Broken down by body, noise class, inferred vs explicit and catalog vs invented, with false positives per hard negative kind. Baselines: naive and prototype.
- Issue type: per-class precision, recall and F1, macro F1, accuracy, confusion matrix and rule abstention rate for majority, rules and naive Bayes side by side.
- Grouping: pairwise precision, recall and F1 against group_id, group count and largest group. Baseline: exact match on the cleaned subject.
- Intervals: 95 percent percentile bootstrap over report seeds (2,000 draws, fixed RNG seed), since rows inside one seed are not independent. Written set: Wilson intervals for precision and recall, bootstrap over RFIs for F1.
- src/rfikit/measured.json holds the numbers at run defaults; scripts/make_measured.py rebuilds it and --check fails CI when it is stale. scripts/reproduce_readme.py regenerates every README number.

## Non-goals
- rfikit does not say whether a standard applies, what it requires or whether a design complies. No standard text, titles or clause wording anywhere.
- No language models, logistic regression, PDF or OCR input, multi-label types, equipment tags or priority scores in v0.1. The prototype's length-based priority score is dropped: no label exists to measure it.
- No project platform connectors, server, accounts or upload. English only.

## Version plan
- v0.2: edition consistency across a document set (one base key cited with different years, such as IEEE 80-2000 and IEEE 80-2013), NFPA, UL and ASME grammars, a CSV mode in the demo, top-k similar past RFIs scored by recall at k.
- v0.3: logistic regression and a local model behind the Classifier protocol, scored on the same three sets.

## Demo plan
- Static GitHub Pages site in site/. Paste mode: paste RFI text, see citations highlighted with the body written inside each mark (not color alone), a table of keys and the issue type with its reason; a button loads a synthetic sample by seed. Results page: measured.json as tables for all three sets (per body, per noise class, confusion matrices, grouping), labeled "measured on synthetic data".
- Pyodide core files and the rfikit wheel are served from the Pages origin, not a CDN, with a Content-Security-Policy of connect-src 'self', since pasted text may be real project text. Highlights are built from text nodes, never HTML strings. The browser test fails on any request to another host.
- Design tokens from the synthbiz demo stylesheet. Keyboard use, a label on every control, wide tables scroll in their own box. The page must pass axe, show no console errors and no horizontal overflow at desktop and phone widths.
- examples/: seed 42, 200 RFIs, with its analysis files, marked synthetic data.

## Test plan
- Unit: table-driven cases per body (positives, every hard negative kind, joint prefixes, clauses before and after, list continuation, NESC context present and absent), key formats, rule order, naive Bayes against hand-computed probabilities on a tiny corpus, union-find, Wilson bounds against known values.
- Property (hypothesis): text[start:end] equals the citation text; a random grammar-valid designation rendered in any supported style inside random filler extracts to the same key; output spans never overlap; unrelated text added elsewhere removes no citation and shifts offsets exactly; adversarial input (1 MB of digits, dots and body tokens) finishes within a loose time bound; naive Bayes posteriors sum to 1 and ignore training row order; prefix-filtered pairs equal all-pairs pairs at or above t; raising t only splits groups; scores stay in [0, 1], perfect output scores 1, an extra false positive never raises precision.
- Generator: same seed, byte-identical files; every label matches the text at its offsets; no negative overlaps a citation; checksums verify; no family B template appears in split A.
- Boundaries: cite, classify and group import neither synth nor evaluate; blanking label files and family ids changes no prediction. Regression: golden outputs for examples/ and golden metrics for a fixed seed list; each fixed bug adds a case. Input limits: malformed CSV, BOM, non-UTF-8 bytes, row and field caps give clear errors.
- CI: ruff, mypy --strict, pytest, at least 90 percent line coverage on src/rfikit, browser test in its own job.

## The prototype
rfi_analyzer.py and the stray one-byte file named src are deleted in PR 2 and stay in git history, which is not rewritten. Its six regex groups are ported unchanged (finditer for spans) to benchmarks/prototype_baseline.py, so the README shows prototype and rebuild scores on the same labels. The old README line and repository description are replaced with plain text.

## PR sequence
One feature per PR, commits under about 800 lines except generated data.
1. spec: this file.
2. scaffold: delete the prototype, LICENSE fixed to the year the repo was created, plain stub README, pyproject, types, CI, and ADRs (stdlib and local-first, designations only, only evaluate reads labels, prefix-filter grouping). Then the main ruleset (PR and CI check required), Dependabot and CodeQL, since the repo is already public and main is unprotected.
3. written set: annotation guide, heldout/ files with sha256, label readers.
4. generator: catalog, family A templates, family B in its own commit, negatives, noise, groups, manifest.
5. extractor: textnorm and cite with unit and property tests; prototype baseline port.
6. extraction evaluation: evaluate, metrics, intervals, measured.json, make_measured.py, extraction benchmark.
7. issue types: rules, naive Bayes, majority, model JSON, evaluation.
8. grouping: TF-IDF, prefix filtering, union-find, evaluation, grouping benchmark.
9. CLI and analysis output, examples/.
10. demo in site/ with the browser test and its ADR.
11. docs: README, DATA.md, THIRD_PARTY_NOTICES.md, SECURITY.md, CHANGELOG.md, issue templates, screenshots; release v0.1.0.
If the schedule slips, 7 and 8 move after 10 and ship in a minor release.

## License
- All rights reserved, see LICENSE, with the year the repo was created (2025). README License section: "All rights reserved. You may view the code and run it to evaluate it. Commercial use needs a paid license from Mehmet Tuzunkan: https://www.linkedin.com/in/mstuzunkan". The same notice goes in README.txt in every output and data folder, the analysis files, the model JSON and the demo footer. Package metadata: license = "LicenseRef-Proprietary", license-files = ["LICENSE"], no OSI classifiers. Outside code contributions are not accepted; bug reports by issue are fine.
- Third-party parts keep their own licenses, listed in THIRD_PARTY_NOTICES.md: Pyodide in the demo; hypothesis, pytest, ruff and mypy as dev tools. The designation catalog, templates, phrase lists and stop words are written for this repo. DATA.md states that all data is synthetic and records any outside list with its license.

## Liability notes
- Every analysis file and the demo footer say: "Decision support only, not legal, engineering, tax, accounting or assurance advice. No guarantee of compliance. rfikit does not say whether a standard applies or what it requires; check every citation against the official standard. False positives and misses are expected; the measured rates are shown."
- Output is called an analysis. Issue types and groups are suggestions with reasons.
- Standard text stays with its owners: code, data and output hold only designations and clause numbers, which are identifiers. IEEE, NESC, IEC, ANSI, ASTM and NEMA are trademarks of their owners, named only to identify their documents; no affiliation or endorsement.
- All data is synthetic: project codes and role ids, no real company, facility, project or person, nothing from any employer. Measured rates come from synthetic data and say so; rates on real RFI logs will differ.
- Pasted text stays in the browser, and the CLI makes no network calls.
