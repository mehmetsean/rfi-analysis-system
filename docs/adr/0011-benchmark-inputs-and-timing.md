# 11. Benchmark inputs and timing

Status: Accepted

## Context

The spec asks for extraction precision, recall and characters per second for the naive baseline, the prototype regexes and rfikit, and a linear time check on adversarial input. A full run has to stay short on a laptop and the CI run has to be fast and not flaky.

## Decision

Speed inputs. The seed corpus is family A on report seeds 101, 102 and 103, 600 RFIs each, with the subject, question and response of every RFI timed as separate texts. The written set is heldout/input/rfis.csv in the same way. The adversarial input is the text that scripts/make_bench_inputs.py writes (the repeated unit "IEEE 1547 and "), built in memory at 1 MiB and 2 MiB, so the generator and the benchmark cannot drift apart.

Accuracy. Precision and recall are read from src/rfikit/measured.json, never scored again. The table shows strict and overlap span for every method, because the baselines have no key levels (ADR 8). The seed corpus rows show the full run on seeds 101 to 130, not the three seeds used for speed, and the file says so.

Timing. One warm-up, then the median of 5 runs with time.perf_counter, with the minimum and maximum. rfikit is timed with extract on each text, without the cross-column NESC context, so all three methods see the same texts.

Quick mode. Seed 101 only, 40 RFIs. The written set and adversarial input of 128 KiB and 256 KiB, five timed runs after one warm-up (the default, as in the full run). It writes no file unless --out is given. It fails when a method finds no citations or when the rfikit time ratio of the two adversarial sizes is above 3.5. A quadratic extractor gives a ratio near 4 when the input doubles and a linear one measures about 2.0 in quick mode, so 3.5 catches the first and leaves margin for a noisy runner. The full run prints the ratio next to the spec bound of 3 and does not fail on it.

Options considered:

- Score again inside the benchmark. A second scoring path could disagree with measured.json.
- Time one big concatenated text for the corpus. It hides the per-text cost that real use has.
- Assert absolute speeds in CI. Runner speed varies, and the spec says no absolute bound.

## Consequences

Numbers in docs/benchmark.md come from one machine and one run. They are rebuilt by running the command in the file, which overwrites docs/benchmark.md. benchmarks/ is outside the coverage source, as before; tests/test_bench.py covers the pure parts and a quick run.
