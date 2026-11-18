from hypothesis import given, settings
from hypothesis import strategies as st

from rfikit.evaluate import NEGATIVE_KINDS, NOISE_CLASSES
from rfikit.synth import GenParams, generate
from synth_helpers import EM_DASH, EN_DASH, column_text

PARAMS = st.builds(
    GenParams,
    noise_rate=st.sampled_from([0.0, 0.35, 1.0]),
    invented_rate=st.sampled_from([0.0, 0.3, 1.0]),
    response_rate=st.sampled_from([0.0, 0.5, 1.0]),
    greeting_rate=st.sampled_from([0.0, 1.0]),
    families=st.sampled_from([("A",), ("B",), ("A", "B")]),
)


@settings(max_examples=120, deadline=None)
@given(
    seed=st.integers(min_value=0, max_value=2**40),
    n=st.integers(min_value=1, max_value=10),
    params=PARAMS,
)
def test_offsets_hold_for_any_seed(seed: int, n: int, params: GenParams) -> None:
    corpus = generate(seed, n, params)
    assert len(corpus.rfis) == n
    for g in corpus.rfis:
        assert g.family in params.families
        spans = []
        for c in g.citations:
            text = column_text(g, c.column)
            assert 0 <= c.start < c.end <= len(text)
            assert text[c.start : c.end] == c.text
            assert c.noise_class in NOISE_CLASSES
            if c.clause_start is not None and c.clause_end is not None:
                assert 0 <= c.clause_start < c.clause_end <= len(text)
                if not c.inferred:
                    assert c.clause_end <= c.start or c.clause_start >= c.end
            spans.append((c.column, c.start, c.end))
        for neg in g.negatives:
            text = column_text(g, neg.column)
            assert text[neg.start : neg.end] == neg.text
            assert neg.kind in NEGATIVE_KINDS
            spans.append((neg.column, neg.start, neg.end))
        spans.sort()
        for left, right in zip(spans, spans[1:], strict=False):
            if left[0] == right[0]:
                assert left[2] <= right[1]
        joined = g.rfi.subject + g.rfi.question + g.rfi.response
        assert EN_DASH not in joined and EM_DASH not in joined


@settings(max_examples=60, deadline=None)
@given(seed=st.integers(min_value=0, max_value=2**40))
def test_same_seed_same_corpus(seed: int) -> None:
    assert generate(seed, 5) == generate(seed, 5)
