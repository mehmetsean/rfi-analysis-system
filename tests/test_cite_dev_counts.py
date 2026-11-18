from cite_dev_counts import count


def test_counts_on_one_seed() -> None:
    totals = count(range(1, 2), 100)
    assert totals["rfis"] == 100
    assert totals["in_scope"] == totals["misspelled"] + totals["not_misspelled"]
    assert totals["found_exact_span"] == totals["not_misspelled"]
    assert totals["false_positives"] == 0
