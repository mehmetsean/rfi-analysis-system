# 11. Benchmark inputs and timing

Status: Accepted

## Context

The spec asks for extraction precision, recall and characters per second for the naive baseline, the prototype regexes and rfikit, and a linear time check on hostile input. A full run has to stay short on a laptop and the CI run has to be fast and not flaky.

## Decision

Speed inputs. The seed corpus is family A on report seeds 101, 102 and 103, 600 RFIs each, with the subject, question and response of every RFI timed as separate texts. The written set is heldout/input/rfis.csv in the same way. The hostile input is the text that scripts/make_bench_inputs.py writes (the repeated unit "IEEE 1547 and "), built in memory at 1 MiB and 2 MiB, so the generator and the benchmark cannot drift apart.

Accuracy. Precision and recall are read from src/rfikit/measured.json, never scored again. The table shows strict and overlap span for every method, because the baselines have no key levels (ADR 8). The seed corpus rows show the full run on seeds 101 to 130, not the three seeds used for speed, and the file says so.

Timing. One warm-up, then the median of 5 runs with time.perf_counter, with the minimum and maximum. rfikit is timed with extract on each text, without the cross-column NESC context, so all three methods see the same texts.

Quick mode. 1 RFI seed of 40 RFIs, the written set and hostile input of 128 KiB and 256 KiB, one timed run. It writes no file unless --out is given. It fails when a method finds no citations or when the rfikit time ratio of the two hostile sizes is above 6. The spec bound is 3; the looser bound keeps CI from failing on noisy small runs. The full run reports the ratio against 3.

Options considered:

- Score again inside the benchmark. A second scoring path could disagree with measured.json.
- Time one big concatenated text for the corpus. It hides the per-text cost that real use has.
- Assert absolute speeds in CI. Runner speed varies, and the spec says no absolute bound.

## Consequences

Numbers in docs/benchmark.md come from one machine and one run. They are rebuilt by hand with the command in the file. benchmarks/ is outside the coverage source, as before; tests/test_bench.py covers the pure parts and a quick run.
