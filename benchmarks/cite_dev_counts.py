from collections import Counter

from rfikit.cite import extract_rfi
from rfikit.synth import GenParams, generate
from rfikit.synth.model import CitationLabel, GeneratedRfi, NegativeLabel
from rfikit.types import Citation

SEEDS = range(1, 11)
PARAMS = GenParams(families=("A",))


def overlap(cite: Citation, mark: CitationLabel | NegativeLabel) -> bool:
    return (
        cite.column == mark.column and cite.start < mark.end and mark.start < cite.end
    )


def same_span(found: list[Citation], label: CitationLabel) -> Citation | None:
    for cite in found:
        if cite.column == label.column and (cite.start, cite.end) == (
            label.start,
            label.end,
        ):
            return cite
    return None


def false_positives(row: GeneratedRfi, found: list[Citation]) -> int:
    count = 0
    for cite in found:
        marks = [n for n in row.negatives if overlap(cite, n)]
        outs = [c for c in row.citations if c.scope == "out" and overlap(cite, c)]
        ins = [c for c in row.citations if c.scope == "in" and overlap(cite, c)]
        if marks or outs or not ins:
            count += 1
    return count


def count(seeds: range = SEEDS, n: int = 600) -> dict[str, int]:
    totals: Counter[str] = Counter()
    for seed in seeds:
        for row in generate(seed, n, PARAMS).rfis:
            totals["rfis"] += 1
            found = extract_rfi(row.rfi)
            totals["false_positives"] += false_positives(row, found)
            spoiled = any(c.noise_class == "misspelled" for c in row.citations)
            for label in row.citations:
                if label.scope != "in":
                    continue
                totals["in_scope"] += 1
                hit = same_span(found, label)
                if label.noise_class == "misspelled":
                    totals["misspelled"] += 1
                    totals["misspelled_" + label.key.split(" ")[0]] += 1
                    if hit:
                        totals["misspelled_found"] += 1
                    continue
                totals["not_misspelled"] += 1
                if hit:
                    totals["found_exact_span"] += 1
                    if hit.designation.key() == label.key:
                        totals["found_right_key"] += 1
                    elif spoiled:
                        totals["clause_cases"] += 1
    return dict(totals)


def main() -> None:
    totals = count()
    for name in sorted(totals):
        print(name, totals[name])


if __name__ == "__main__":
    main()
