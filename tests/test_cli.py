import pytest

from rfikit import __version__
from rfikit.cli import main


def test_no_command(capsys: pytest.CaptureFixture[str]) -> None:
    assert main([]) == 0
    out = capsys.readouterr().out
    assert __version__ in out
    assert "not built yet" in out


@pytest.mark.parametrize("name", ["extract", "analyze", "generate", "evaluate"])
def test_stub_command(name: str, capsys: pytest.CaptureFixture[str]) -> None:
    assert main([name, "x"]) == 1
    captured = capsys.readouterr()
    assert "not built yet" in captured.err
    assert captured.out == ""


def test_unknown_command(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["nope"]) == 2
    assert "Unknown command" in capsys.readouterr().err


def test_version_flag(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["--version"]) == 0
    assert capsys.readouterr().out == __version__ + "\n"
