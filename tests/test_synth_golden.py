import os
import subprocess
import sys
from pathlib import Path

from rfikit.synth import generate, render_files
from rfikit.synth.files import sha256

GOLDEN_SEED_42_N_40 = {
    "README.txt": ("d1aae071225a6effcefa4eedc754475144debf248dbeb31149e09175e693f17e"),
    "input/README.txt": (
        "41bda584b68d54a473b9e9b7e5c2331c64e59013c4dcb4080b45d803cb6e36a6"
    ),
    "input/rfis.csv": (
        "2742ccb190d75180b7fea2033f8a04040d02a89a3cd9bbea6b9f9442baa2ba3b"
    ),
    "labels/README.txt": (
        "e7eada984ff0dc4be2ac9e8fbee06739a7a77a60f20951b2565e6b016040ae08"
    ),
    "labels/citations.csv": (
        "55d36e2b0f237d5cf656a987514a2690c014376cbababc88c67e2df8939b568f"
    ),
    "labels/negatives.csv": (
        "ed2e032a15bbcb32f2882b05f2fb220521cab44d12ec8150e718e8b3f5d9e695"
    ),
    "labels/rfis.csv": (
        "c1543bc9f2086031b3b5c4b47c16aecdeda5e9c135f36395c82cb6cf5df5f1c3"
    ),
    "manifest.json": (
        "45d27ac28062ec0748e854e509fbd09a4ceab50549df1d07ae7c81eef2381762"
    ),
}

SCRIPT = (
    "import sys\n"
    "from pathlib import Path\n"
    "from rfikit.synth import generate, write_corpus\n"
    "write_corpus(generate(42, 120), Path(sys.argv[1]))\n"
)


def test_golden_hashes_for_seed_42() -> None:
    files = render_files(generate(42, 40))
    assert {name: sha256(data) for name, data in files.items()} == GOLDEN_SEED_42_N_40


def run_with_hash_seed(out: Path, hash_seed: str) -> None:
    env = dict(os.environ)
    env["PYTHONHASHSEED"] = hash_seed
    subprocess.run(
        [sys.executable, "-c", SCRIPT, str(out)], check=True, env=env, timeout=120
    )


def test_bytes_do_not_depend_on_the_hash_seed(tmp_path: Path) -> None:
    run_with_hash_seed(tmp_path / "one", "1")
    run_with_hash_seed(tmp_path / "two", "4242")
    names = sorted(
        p.relative_to(tmp_path / "one") for p in (tmp_path / "one").rglob("*")
    )
    assert len(names) >= 8
    for name in names:
        first = tmp_path / "one" / name
        if first.is_file():
            assert first.read_bytes() == (tmp_path / "two" / name).read_bytes(), name


def test_subprocess_bytes_match_the_in_process_bytes(tmp_path: Path) -> None:
    run_with_hash_seed(tmp_path / "x", "0")
    for name, data in render_files(generate(42, 120)).items():
        assert (tmp_path / "x" / name).read_bytes() == data, name
