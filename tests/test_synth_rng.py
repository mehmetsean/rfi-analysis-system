import ast
from pathlib import Path

import pytest

from rfikit.synth.rng import Rng

SYNTH = Path(__file__).resolve().parent.parent / "src" / "rfikit" / "synth"
BANNED_CALLS = {
    "randint",
    "randrange",
    "choice",
    "choices",
    "sample",
    "shuffle",
    "uniform",
    "gauss",
    "getrandbits",
    "randbytes",
    "triangular",
    "betavariate",
    "expovariate",
}


def test_same_seed_same_numbers() -> None:
    a = Rng(7)
    b = Rng(7)
    assert [a.unit() for _ in range(5)] == [b.unit() for _ in range(5)]


def test_known_first_value() -> None:
    assert Rng(42).unit() == 0.6394267984578837


def test_below_stays_in_range() -> None:
    rng = Rng(1)
    values = {rng.below(5) for _ in range(200)}
    assert values == {0, 1, 2, 3, 4}


def test_between_is_inclusive() -> None:
    rng = Rng(2)
    values = {rng.between(3, 5) for _ in range(100)}
    assert values == {3, 4, 5}


def test_below_rejects_zero() -> None:
    with pytest.raises(ValueError):
        Rng(1).below(0)


def test_seed_must_be_int() -> None:
    with pytest.raises(TypeError):
        Rng(True)
    with pytest.raises(TypeError):
        Rng(1.5)  # type: ignore[arg-type]


def test_weighted_skips_zero_weight() -> None:
    rng = Rng(3)
    assert {rng.weighted("abc", [0, 5, 1]) for _ in range(100)} == {"b", "c"}


def test_mix_keeps_items() -> None:
    rng = Rng(4)
    items = list(range(20))
    rng.mix(items)
    assert sorted(items) == list(range(20))
    assert items != list(range(20))


def test_pick_and_chance() -> None:
    rng = Rng(5)
    assert rng.pick(["x"]) == "x"
    assert not rng.chance(0.0)
    assert rng.chance(1.0)


def test_synth_modules_use_only_random_and_no_math() -> None:
    for path in sorted(SYNTH.glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                assert all(a.name != "math" for a in node.names), path
            if isinstance(node, ast.ImportFrom):
                assert node.module != "math", path
            if isinstance(node, ast.Attribute):
                assert node.attr not in BANNED_CALLS, (path, node.attr)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                assert node.func.id not in ("hash", "id"), path


def test_negative_seed_is_rejected() -> None:
    with pytest.raises(ValueError, match="negative"):
        Rng(-1)


def test_only_rng_imports_random_and_nothing_seeds_it() -> None:
    for path in sorted(SYNTH.glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            names: list[str] = []
            if isinstance(node, ast.Import):
                names = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom):
                names = [node.module or ""]
            if "random" in names:
                assert path.name == "rng.py", path
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                assert node.func.attr != "seed", path
