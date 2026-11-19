from pathlib import Path

import pytest
import reproduce_readme

DOC = {
    "full": {
        "sets": {
            name: {
                "methods": {
                    "rfikit": {
                        "levels": {
                            "strict": {"precision": 0.5, "recall": 0.25},
                            "overlap": {"precision": 1.0, "recall": 0.75},
                        }
                    }
                }
            }
            for name in ("A", "B", "written")
        }
    }
}


def test_block_has_one_row_per_level_and_set() -> None:
    block = reproduce_readme.build_block(DOC)
    assert "| Strict | Set A | 0.500 | 0.250 |" in block
    assert "| Overlap | Written set | 1.000 | 0.750 |" in block
    assert block.count("\n| ") == 6 + 1


def test_replace_block_keeps_text_around_it() -> None:
    text = f"top\n{reproduce_readme.START}\nold\n{reproduce_readme.END}\nend\n"
    out = reproduce_readme.replace_block(text, "NEW")
    assert out == "top\nNEW\nend\n"


def test_replace_block_needs_markers() -> None:
    with pytest.raises(SystemExit):
        reproduce_readme.replace_block("no markers", "NEW")


def test_limits_fail_when_a_phrase_is_missing() -> None:
    problems = reproduce_readme.check_limits("32 MiB")
    assert any("4 MiB" in p for p in problems)


def test_limits_pass_with_all_phrases() -> None:
    text = "32 MiB 4 MiB 100,000 rows 100,000 characters"
    assert reproduce_readme.check_limits(text) == []


def test_memory_number_must_be_in_adr(tmp_path: Path) -> None:
    problems = reproduce_readme.check_memory("peak 999,999,999 bytes")
    assert problems == ["999,999,999 is not in 0010-analyze-output-folder.md"]


def test_repo_readme_is_current() -> None:
    assert reproduce_readme.main(["--check"]) == 0
