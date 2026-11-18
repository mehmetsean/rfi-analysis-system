import ast
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent / "src" / "rfikit"
BLOCKED = {"socket", "urllib", "http", "ssl", "requests", "subprocess"}


def imported(path: Path) -> set[str]:
    found: set[str] = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            found.update(a.name.split(".")[0] for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            found.add(node.module.split(".")[0])
    return found


def test_no_network_or_process_imports() -> None:
    paths = sorted(SRC.rglob("*.py"))
    assert len(paths) > 20
    for path in paths:
        assert imported(path) & BLOCKED == set(), path.name


def test_the_check_sees_imports(tmp_path: Path) -> None:
    sample = tmp_path / "x.py"
    sample.write_text("import urllib.request\nfrom socket import socket\n")
    assert imported(sample) == {"urllib", "socket"}
