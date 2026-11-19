import base64
import hashlib
import io
import json
import sys
import tarfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import build_site  # noqa: E402


def make_tar(path: Path, members: dict[str, bytes]) -> None:
    with tarfile.open(path, "w:bz2") as tar:
        for name, data in members.items():
            info = tarfile.TarInfo(name)
            info.size = len(data)
            tar.addfile(info, io.BytesIO(data))


def test_check_sha256_accepts_and_refuses(tmp_path: Path) -> None:
    f = tmp_path / "a.bin"
    f.write_bytes(b"hello")
    good = hashlib.sha256(b"hello").hexdigest()
    build_site.check_sha256(f, good)
    with pytest.raises(SystemExit, match="sha256"):
        build_site.check_sha256(f, "0" * 64)


def sri_of(data: bytes) -> str:
    return base64.b64encode(hashlib.sha384(data).digest()).decode()


def good_members() -> dict[str, bytes]:
    return {f"pyodide/{n}": n.encode() for n in build_site.CORE_FILES}


def test_extract_core_copies_only_the_listed_files(tmp_path: Path) -> None:
    members = good_members()
    members["pyodide/python"] = b"#!/bin/sh\nexit 1\n"
    members["../evil.txt"] = b"x"
    tar = tmp_path / "core.tar.bz2"
    make_tar(tar, members)
    out = tmp_path / "out"
    out.mkdir()
    build_site.extract_core(tar, out, sri_of(b"pyodide.js"))
    assert sorted(p.name for p in out.iterdir()) == sorted(build_site.CORE_FILES)
    assert not (tmp_path / "evil.txt").exists()
    assert not (out / "python").exists()


def test_extract_core_fails_when_a_file_is_missing(tmp_path: Path) -> None:
    tar = tmp_path / "core.tar.bz2"
    make_tar(tar, {"pyodide/pyodide.js": b"x"})
    out = tmp_path / "out"
    out.mkdir()
    with pytest.raises(SystemExit, match="missing"):
        build_site.extract_core(tar, out, sri_of(b"x"))


def test_extract_core_uses_the_exact_path(tmp_path: Path) -> None:
    members = {f"other/{n}": b"x" for n in build_site.CORE_FILES}
    tar = tmp_path / "core.tar.bz2"
    make_tar(tar, members)
    with pytest.raises(SystemExit, match="missing"):
        build_site.extract_core(tar, tmp_path / "out", sri_of(b"x"))


def test_extract_core_checks_the_sri_before_writing(tmp_path: Path) -> None:
    tar = tmp_path / "core.tar.bz2"
    make_tar(tar, good_members())
    out = tmp_path / "out"
    with pytest.raises(SystemExit, match="sha384"):
        build_site.extract_core(tar, out)
    assert not out.exists()


def test_check_sri_compares_sha384() -> None:
    build_site.check_sri(b"abc", sri_of(b"abc"))
    with pytest.raises(SystemExit, match="sha384"):
        build_site.check_sri(b"abc", "AAAA")


def test_write_manifest(tmp_path: Path) -> None:
    build_site.write_manifest(tmp_path, ["b-1.whl", "a-1.whl"])
    data = json.loads((tmp_path / "manifest.json").read_text("utf-8"))
    assert data == {
        "pyodide": build_site.PYODIDE_VERSION,
        "wheels": ["a-1.whl", "b-1.whl"],
    }


def test_constants_look_right() -> None:
    assert len(build_site.TARBALL_SHA256) == 64
    assert build_site.PYODIDE_URL.startswith(
        "https://github.com/pyodide/pyodide/releases/download/"
    )
    assert build_site.PYODIDE_VERSION in build_site.PYODIDE_URL


def test_fetch_tarball_refuses_a_bad_cached_file(tmp_path: Path) -> None:
    cached = tmp_path / build_site.TARBALL
    cached.write_bytes(b"not the archive")
    with pytest.raises(SystemExit, match="sha256"):
        build_site.fetch_tarball(tmp_path)
    assert not cached.exists()


def test_download_refuses_non_https(tmp_path: Path) -> None:
    with pytest.raises(SystemExit, match="https"):
        build_site.download("http://example.com/x", tmp_path / "x")
    assert not (tmp_path / "x").exists()


def test_clear_stays_inside_the_repo(tmp_path: Path) -> None:
    with pytest.raises(SystemExit, match="_site"):
        build_site.clear(tmp_path / "_site")
    with pytest.raises(SystemExit, match="_site"):
        build_site.clear(ROOT / "docs")


def test_main_fails_on_a_bad_sri(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "repo"
    (root / "site").mkdir(parents=True)
    (root / "site" / "index.html").write_text("x", "utf-8")
    tar = tmp_path / "core.tar.bz2"
    make_tar(tar, good_members())
    monkeypatch.setattr(build_site, "ROOT", root)
    monkeypatch.setattr(build_site, "fetch_tarball", lambda cache: tar)
    monkeypatch.setattr(build_site, "build_wheel", lambda target, out: "x.whl")
    with pytest.raises(SystemExit, match="sha384"):
        build_site.main(["--cache", str(tmp_path / "cache")])
    assert not (root / "_site" / "pyodide" / "pyodide.js").exists()


def test_main_builds_the_site_with_measured_json(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "repo"
    (root / "site").mkdir(parents=True)
    (root / "site" / "index.html").write_text("x", "utf-8")
    (root / "src" / "rfikit").mkdir(parents=True)
    (root / "src" / "rfikit" / "measured.json").write_text('{"a": 1}', "utf-8")
    tar = tmp_path / "core.tar.bz2"
    make_tar(tar, good_members())

    def fake_extract(tarball: Path, out: Path) -> None:
        out.mkdir(parents=True)
        (out / "pyodide.js").write_text("x", "utf-8")

    def fake_wheel(target: str, out: Path) -> str:
        (out / "rfikit-0-py3-none-any.whl").write_bytes(b"w")
        return "rfikit-0-py3-none-any.whl"

    monkeypatch.setattr(build_site, "ROOT", root)
    monkeypatch.setattr(build_site, "fetch_tarball", lambda cache: tar)
    monkeypatch.setattr(build_site, "extract_core", fake_extract)
    monkeypatch.setattr(build_site, "build_wheel", fake_wheel)
    assert build_site.main(["--cache", str(tmp_path / "cache")]) == 0
    site = root / "_site"
    assert (site / "measured.json").read_text("utf-8") == '{"a": 1}'
    assert (site / "index.html").is_file()
    assert json.loads((site / "manifest.json").read_text("utf-8"))["wheels"] == [
        "rfikit-0-py3-none-any.whl"
    ]
