import os
import subprocess
import sys
from pathlib import Path

from rfikit.synth import generate, render_files
from rfikit.synth.files import sha256

GOLDEN_SEED_42_N_40 = {
    "README.txt": ("203d4517005ccf625b8e1d1a45af55df245e720c2f3ef076ab6a85fb3edb4503"),
    "input/README.txt": (
        "41bda584b68d54a473b9e9b7e5c2331c64e59013c4dcb4080b45d803cb6e36a6"
    ),
    "input/rfis.csv": (
        "d53050f27a120dfb89bc57e9a90291636a9dbc942b0081bdb25c8b24a23108f8"
    ),
    "labels/README.txt": (
        "e7eada984ff0dc4be2ac9e8fbee06739a7a77a60f20951b2565e6b016040ae08"
    ),
    "labels/citations.csv": (
        "bdd7600d7e618ccaf7d17896c70137798183843da72f8c33e8e7e02d3d8eb567"
    ),
    "labels/negatives.csv": (
        "d2a0b515a550f8fda7a7a45480b5982c2b4e51c6d951390069416930793dbe3c"
    ),
    "labels/rfis.csv": (
        "c8680cb786b213b585da33c0e907e94b7c8544cffa14b91ac6b93708185c6ea8"
    ),
    "manifest.json": (
        "c7653d14083450bad5466603b845536d898abedfbbbe00b1b0133adf3dead9f2"
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
