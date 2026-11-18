import pytest

from rfikit import __version__
from rfikit.cli import main


def test_no_command(capsys: pytest.CaptureFixture[str]) -> None:
    assert main([]) == 0
    out = capsys.readouterr().out
    assert __version__ in out
    assert "not built yet" in out


def test_known_command(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["extract", "notes.txt"]) == 0
    assert "not built yet" in capsys.readouterr().out


def test_unknown_command(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["nope"]) == 2
    assert "Unknown command" in capsys.readouterr().err


def test_version_flag(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["--version"]) == 0
    assert __version__ in capsys.readouterr().out
