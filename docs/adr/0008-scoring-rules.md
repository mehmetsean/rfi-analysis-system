# 8. Scoring rules for extraction

Status: Accepted

## Context

The spec fixes four levels (strict span, overlap span, full key, base key), a clause line, breakdowns, baselines and a leak check, but leaves several choices open. Each one changes a published number, so each is written down here, and any later change to a rule is logged here.

## Decision

Gold. Only labels with scope "in" are gold. An out-of-scope label is never a miss. A prediction that overlaps an out-of-scope label has no gold partner unless it also overlaps an in-scope label, so it counts as a false positive at every level, as for any unmatched prediction. It is also reported on its own line: the out-of-scope labels that at least one prediction overlaps, with the total. This follows the spec ("a false positive of kind out_of_scope"); the annotation guide only says such labels are never misses.

Levels. Strict span: same column, start and end, one to one. Overlap span: one to one by the two-pointer sweep per column. Full key and base key: a multiset per RFI, with the same keys on both sides, so a wrong key is one false positive and one miss.

Clause line. Gold clauses are the clause offsets of every in-scope label that has them (an inferred bare NESC rule included, since its clause offsets are its span). Predicted clauses are the clause offsets of every prediction that has them. They match when column, clause start and clause end are equal. The line does not look at the citation, so a clause bound to the wrong designation still counts as found here; the full key shows that error.

Hard negatives. For each hard negative kind the report gives the number of labels and the number that at least one prediction overlaps. The pooled line adds the kinds and is the one with a Wilson interval on the written set. Counting labels, not predictions, keeps the rate between 0 and 1.

Breakdowns. Groups are body, noise class, inferred or explicit, and catalog real or invented. Each group has recall at strict span, overlap span and "key". Key here means the overlap partner has the same full key; it is a per-citation test and can differ a little from the multiset full key line. Precision needs a prediction side. Predictions carry a body and an inferred flag, so those two groups have precision. They do not carry a noise class or a catalog value, so for those two groups precision is n/a and the file lists them under no_precision_dims. A group with no gold has recall n/a; a group with no predictions has precision n/a. A macro average skips every n/a and reports how many it skipped.

Intervals. Generated sets: 95 percent percentile bootstrap over report seeds, 2,000 draws, random.Random(4242) using only random(). Draws are sorted and the interval is the values at index floor(0.025 x draws) and draws - 1 - that index. If any draw has an undefined ratio the interval is n/a. The A minus B gap uses the same draws for both families. With fewer than two seeds there is no interval. Written set: Wilson 95 percent intervals on precision, recall and the pooled hard negative rate; the counts are treated as independent.

Families. Family A and family B sets are generated apart with GenParams(families=("A",)) and ("B",), 600 RFIs per seed.

Leak check. "Cleaned" means rfikit.textnorm.clean (the one-to-one character map), then lower case by casefold, then every run of white space turned into one space and the ends stripped. The key of an RFI is the pair of cleaned subject and cleaned question; the response is ignored. The pool holds the keys of train and tune seeds 1 to 10, 600 RFIs each, for family A and family B. A report RFI whose key is in the pool is dropped with all its labels; the dropped count and fraction are stored per family. This finds exact repeats after cleanup. It does not find paraphrases or a repeat that differs by a misspelled body.

Methods. evaluate takes extra span methods as callables from text to a list of (body, start, end). The package never imports benchmarks/; scripts/make_measured.py passes the prototype and the naive baseline. A method is run on each column alone. Its hits are made non-overlapping first (sorted by start, longest first, a hit that starts inside the last kept hit is dropped), because the sweep needs non-overlapping spans and one mention should not count twice. This helps the baselines a little, which is the safe direction. Baselines are scored at strict and overlap span, overall and by body, so the NESC line is the body NESC group. Their key levels are not computed.

The evaluate function reads one folder written by write_corpus (one seed), splits it by the family label, and adds the written folder if given. It makes no interval, since one seed gives none. A family label other than A or B in that folder raises a LabelError that names the value, so no RFI is silently left out. evaluate_seeds generates the report seeds in memory and is what make_measured.py uses.

Options considered:

- Count a hit on an out-of-scope label as ignored. It hides a real cost of the grammar.
- Count hard negative false positives as predictions. A prediction can touch two labels and the pooled rate could pass 1.
- Per-citation key test for the headline full key. It needs a rule for which of two equal keys pairs with which citation.
- Merge baseline hits by body instead of by length. More code, no clearer meaning.
- Paraphrase-aware leak check. Needs a similarity measure that v0.2 only adds later.

## Consequences

Numbers on the three sets are comparable because one function scores them. The leak fraction is a lower bound. Noise class and catalog tables show recall only. Changing any rule above changes measured.json and must be logged here.
