import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import make_measured
import pytest

from eval_helpers import make_folder
from rfikit import __version__, measured
from rfikit.evaluate import EvalPlan, evaluate, evaluate_seeds
from rfikit.measured import (
    CI_PLAN,
    FULL_PLAN,
    build_block,
    build_doc,
    make_ratios,
    render,
    summarize,
)
from rfikit.notice import LICENSE_LINE

ROOT = Path(__file__).resolve().parent.parent
SHIPPED = ROOT / "src" / "rfikit" / "measured.json"
SMALL = EvalPlan(report_seeds=(101, 102, 103), n=30, train_seeds=(1,), draws=40)


def tiny_block(tmp_path: Path) -> dict[str, Any]:
    folder = make_folder(tmp_path / "data")
    written = make_folder(tmp_path / "written", second_family="written")
    return summarize(evaluate(folder, written, SMALL))


def test_tiny_block_levels(tmp_path: Path) -> None:
    block = tiny_block(tmp_path)
    a = block["sets"]["A"]["methods"]["rfikit"]["levels"]
    b = block["sets"]["B"]["methods"]["rfikit"]["levels"]
    w = block["sets"]["written"]["methods"]["rfikit"]["levels"]
    assert a["strict"] == {
        "tp": 2,
        "fp": 0,
        "fn": 0,
        "precision": 1.0,
        "recall": 1.0,
        "f1": 1.0,
    }
    assert b["strict"]["precision"] == 0.333333
    assert b["strict"]["recall"] == 0.5
    assert w["strict"]["precision"] == 0.6
    assert w["strict"]["recall"] == 0.75
    assert w["strict"]["f1"] == 0.666667
    assert a["clause"]["recall"] == 1.0
    assert b["clause"]["precision"] is None
    assert b["clause"]["recall"] is None
    assert b["clause"]["f1"] is None


def test_tiny_block_has_no_intervals_for_one_seed(tmp_path: Path) -> None:
    block = tiny_block(tmp_path)
    a = block["sets"]["A"]["methods"]["rfikit"]
    assert "ci" not in a["levels"]["strict"]
    assert "wilson" not in a["levels"]["strict"]
    assert "gap_a_minus_b" not in block
    assert block["sets"]["A"]["seeds"] == 1
    assert block["sets"]["written"]["seeds"] == 0


def test_written_set_gets_wilson_only(tmp_path: Path) -> None:
    block = tiny_block(tmp_path)
    w = block["sets"]["written"]["methods"]["rfikit"]
    low, high = w["levels"]["strict"]["wilson"]["precision"]
    assert low <= 0.6 <= high
    assert "ci" not in w["levels"]["strict"]
    pooled = w["hard_negatives"]["pooled"]
    assert (pooled["total"], pooled["hit"], pooled["rate"]) == (2, 0, 0.0)
    assert pooled["wilson"][0] == 0.0
    assert w["hard_negatives"]["out_of_scope"] == {
        "total": 3,
        "hit": 1,
        "rate": 0.333333,
    }
    assert w["hard_negatives"]["kinds"]["room_number"]["total"] == 1


def test_macro_skips_undefined_groups(tmp_path: Path) -> None:
    block = tiny_block(tmp_path)
    b = block["sets"]["B"]["methods"]["rfikit"]["macro"]["body"]["strict"]
    assert b["precision"] == {"value": 0.25, "used": 2, "skipped": 1}
    assert b["recall"] == {"value": 0.5, "used": 2, "skipped": 1}
    w = block["sets"]["written"]["methods"]["rfikit"]["macro"]["body"]["strict"]
    assert w["precision"] == {"value": 0.666667, "used": 3, "skipped": 0}
    assert w["recall"] == {"value": 0.833333, "used": 3, "skipped": 0}


def test_noise_and_catalog_have_no_precision(tmp_path: Path) -> None:
    block = tiny_block(tmp_path)
    rfikit = block["sets"]["B"]["methods"]["rfikit"]
    mis = rfikit["groups"]["noise"]["misspelled"]["strict"]
    assert mis["precision"] is None
    assert "pred" not in mis
    assert mis["gold"] == 1
    assert mis["recall"] == 0.0
    assert "precision" not in rfikit["macro"]["noise"]["strict"]
    assert "precision" in rfikit["macro"]["body"]["strict"]
    assert rfikit["groups"]["catalog"]["real"]["strict"]["precision"] is None
    assert block["no_precision_dims"] == ["noise", "catalog"]


def test_leak_block_and_plan(tmp_path: Path) -> None:
    block = tiny_block(tmp_path)
    assert block["leak"]["A"] == {"rfis": 1, "dropped": 0, "fraction": 0.0}
    assert block["leak"]["pool_size"] > 0
    assert block["plan"]["draws"] == 40
    assert block["plan"]["bootstrap_seed"] == SMALL.bootstrap_seed
    assert block["plan"]["report_seeds"] == [101, 102, 103]


def test_intervals_and_gap_for_several_seeds() -> None:
    block = summarize(evaluate_seeds(SMALL, None, {"plain": lambda text: []}))
    a = block["sets"]["A"]["methods"]["rfikit"]["levels"]["overlap"]
    b = block["sets"]["B"]["methods"]["rfikit"]["levels"]["overlap"]
    low, high = a["ci"]["recall"]
    assert low <= a["recall"] <= high
    gap = block["gap_a_minus_b"]["rfikit"]["overlap"]["recall"]
    assert gap["value"] == round(a["recall"] - b["recall"], 6)
    assert gap["ci"][0] <= gap["ci"][1]
    plain = block["sets"]["A"]["methods"]["plain"]
    assert plain["levels"]["strict"]["precision"] is None
    assert plain["levels"]["strict"]["ci"]["precision"] is None
    assert "hard_negatives" not in plain
    assert "full" not in plain["levels"]
    assert block["gap_a_minus_b"]["plain"]["strict"]["precision"] == {
        "value": None,
        "ci": None,
    }


def test_make_ratios_without_negatives() -> None:
    ratios = make_ratios({"strict.tp", "strict.fp", "strict.fn"})
    found = ratios({"strict.tp": 3, "strict.fp": 1})
    assert found == {
        "strict.precision": 0.75,
        "strict.recall": 1.0,
        "strict.f1": found["strict.f1"],
    }
    assert not any(name.startswith("neg.") for name in found)


def run_small_build(hash_seed: str) -> str:
    code = (
        "import sys\n"
        "sys.path.insert(0, 'tests')\n"
        "from pathlib import Path\n"
        "from eval_helpers import make_folder\n"
        "from rfikit.evaluate import EvalPlan\n"
        "from rfikit.measured import build_block, render\n"
        "import tempfile\n"
        "folder = make_folder(Path(tempfile.mkdtemp()))\n"
        "plan = EvalPlan(report_seeds=(101, 102), n=40, train_seeds=(1,), draws=30)\n"
        "sys.stdout.write(render(build_block(plan, folder, {})))\n"
    )
    env = {**os.environ, "PYTHONHASHSEED": hash_seed}
    done = subprocess.run(
        [sys.executable, "-c", code],
        cwd=ROOT,
        env=env,
        capture_output=True,
        check=True,
    )
    return done.stdout.decode()


def test_same_bytes_under_two_hash_seeds() -> None:
    assert run_small_build("0") == run_small_build("12345")


def test_render_is_sorted_with_trailing_newline() -> None:
    text = render({"b": 1, "a": {"d": 1, "c": 2}})
    assert text.endswith("}\n")
    assert text.index('"a"') < text.index('"b"')
    assert text.index('"c"') < text.index('"d"')


def test_build_block_matches_summarize(tmp_path: Path) -> None:
    folder = make_folder(tmp_path / "written", second_family="written")
    block = build_block(SMALL, folder, {})
    assert list(block["sets"]) == ["A", "B", "written"]


def test_shipped_file_shape() -> None:
    text = SHIPPED.read_text(encoding="utf-8")
    doc = json.loads(text)
    assert render(doc) == text
    assert doc["rfikit_version"] == __version__
    assert doc["notice"] == LICENSE_LINE
    assert "synthetic data" in doc["data"]
    assert doc["full"]["plan"]["report_seeds"] == list(FULL_PLAN.report_seeds)
    assert doc["ci"]["plan"]["report_seeds"] == list(CI_PLAN.report_seeds)
    assert doc["full"]["plan"]["draws"] == 2000
    for name in ("full", "ci"):
        block = doc[name]
        assert set(block["sets"]) == {"A", "B", "written"}
        assert set(block["sets"]["A"]["methods"]) == {"rfikit", "prototype", "naive"}
        assert "pool_size" in block["leak"]
        assert "gap_a_minus_b" in block
    for char in (chr(0x2013), chr(0x2014)):
        assert char not in text


def test_shipped_ci_block_is_current() -> None:
    assert make_measured.check(SHIPPED, make_measured.compute_ci) == 0


def test_measured_json_is_inside_the_package_folder() -> None:
    assert SHIPPED.parent.name == "rfikit"
    assert SHIPPED.parent.parent.name == "src"


def test_build_doc_has_both_blocks(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    folder = make_folder(tmp_path / "written", second_family="written")
    monkeypatch.setattr(measured, "FULL_PLAN", SMALL)
    monkeypatch.setattr(
        measured,
        "CI_PLAN",
        EvalPlan(report_seeds=(101, 102), n=30, train_seeds=(1,), draws=10),
    )
    doc = build_doc(folder, {})
    assert set(doc) == {"ci", "data", "full", "notice", "rfikit_version"}
    assert doc["full"]["plan"]["report_seeds"] == [101, 102, 103]
    assert doc["ci"]["plan"]["report_seeds"] == [101, 102]
