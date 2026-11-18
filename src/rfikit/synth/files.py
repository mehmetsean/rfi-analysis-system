import csv
import hashlib
import io
import json
from collections.abc import Iterable
from pathlib import Path

from rfikit.synth.model import Corpus

CITATION_HEADER = (
    "rfi_id",
    "column",
    "start",
    "end",
    "clause_start",
    "clause_end",
    "key",
    "base_key",
    "scope",
    "inferred",
    "catalog",
    "noise_class",
)
NEGATIVE_HEADER = ("rfi_id", "column", "start", "end", "kind")
RFI_HEADER = ("rfi_id", "template_id", "family")
INPUT_HEADER = ("rfi_id", "subject", "question", "response")

LICENSE_LINE = (
    "All rights reserved. You may view the code and run it to evaluate it. "
    "Commercial use needs a paid license from Mehmet Tuzunkan: "
    "https://www.linkedin.com/in/mstuzunkan"
)
DISCLAIMER = (
    "Decision support only, not legal, engineering, tax, accounting or assurance "
    "advice. No guarantee of compliance. rfikit does not say whether a standard "
    "applies or what it requires; check every citation against the official "
    "standard. False positives and misses are expected; the measured rates are "
    "shown."
)
OWNERS = (
    "Body names such as IEEE, NESC, IEC, ANSI, ASTM, NEMA, NFPA, UL, ASME, ISA, "
    "TIA, CSA and EN are used only to identify their documents. The names belong "
    "to their owners. This project has no affiliation with or endorsement from "
    "any of them."
)
ROOT_README = "\n".join(
    [
        "Synthetic RFIs with labels for rfikit (synthetic data)",
        "",
        "All data in this folder is synthetic. The generator wrote the RFIs from",
        "templates. Project codes, role ids and disciplines are invented. No real",
        "company, facility, project or person appears in the RFIs. From the",
        "standards, only designations and clause numbers appear, never titles or",
        "standard text.",
        "",
        "Files",
        "- input/rfis.csv: rfi_id, subject, question, response.",
        "- labels/citations.csv and labels/negatives.csv: where the generator put",
        "  each citation and each hard negative, as code point offsets.",
        "- labels/rfis.csv: rfi_id, template_id and family (A or B). Issue type",
        "  and group columns are not written yet.",
        "- input/README.txt and labels/README.txt: short notices for those folders.",
        "- manifest.json: sha256 of every file above, the seed and counts.",
        "The labels come from the generator's record of what it inserted, never",
        "from running an extractor.",
        "",
        "License",
        LICENSE_LINE,
        "",
        "Disclaimer",
        DISCLAIMER,
        OWNERS,
    ]
)
INPUT_README = "\n".join(
    [
        "Synthetic data. The RFIs in this folder were written by the rfikit generator.",
        "",
        LICENSE_LINE,
    ]
)
LABELS_README = "\n".join(
    [
        "Synthetic data. The labels in this folder come from the rfikit generator's",
        "record of where it inserted each item.",
        "",
        LICENSE_LINE,
    ]
)


def _csv(header: tuple[str, ...], rows: Iterable[list[str]]) -> bytes:
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(header)
    writer.writerows(rows)
    return buffer.getvalue().encode("utf-8")


def _number(value: int | None) -> str:
    return "" if value is None else str(value)


def _count(items: Iterable[str]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in items:
        counts[item] = counts.get(item, 0) + 1
    return dict(sorted(counts.items()))


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _label_rows(corpus: Corpus) -> tuple[list[list[str]], list[list[str]]]:
    cite_rows: list[list[str]] = []
    negative_rows: list[list[str]] = []
    order = {"subject": 0, "question": 1, "response": 2}
    for g in corpus.rfis:
        rfi_id = g.rfi.rfi_id
        for c in sorted(g.citations, key=lambda x: (order[x.column], x.start)):
            cite_rows.append(
                [
                    rfi_id,
                    c.column,
                    str(c.start),
                    str(c.end),
                    _number(c.clause_start),
                    _number(c.clause_end),
                    c.key,
                    c.base_key,
                    c.scope,
                    "1" if c.inferred else "0",
                    c.catalog,
                    c.noise_class,
                ]
            )
        for n in sorted(g.negatives, key=lambda x: (order[x.column], x.start)):
            negative_rows.append([rfi_id, n.column, str(n.start), str(n.end), n.kind])
    return cite_rows, negative_rows


def _manifest(corpus: Corpus, files: dict[str, bytes]) -> bytes:
    cites = [c for g in corpus.rfis for c in g.citations]
    in_scope = [c for c in cites if c.scope == "in"]
    negatives = [n for g in corpus.rfis for n in g.negatives]
    params = corpus.params
    manifest = {
        "synthetic": True,
        "generator": {
            "seed": corpus.seed,
            "n": corpus.n,
            "params": {
                "noise_rate": params.noise_rate,
                "invented_rate": params.invented_rate,
                "response_rate": params.response_rate,
                "greeting_rate": params.greeting_rate,
                "families": list(params.families),
            },
        },
        "files": {name: sha256(data) for name, data in sorted(files.items())},
        "counts": {
            "rfis": len(corpus.rfis),
            "families": _count(g.family for g in corpus.rfis),
            "citations_in_scope": len(in_scope),
            "citations_out_of_scope": len(cites) - len(in_scope),
            "citations_per_body": _count(c.key.split(" ")[0] for c in in_scope),
            "citations_inferred": len([c for c in in_scope if c.inferred]),
            "catalog": _count(c.catalog for c in in_scope),
            "noise_classes": _count(c.noise_class for c in in_scope if c.noise_class),
            "negatives": len(negatives),
            "negatives_per_kind": _count(n.kind for n in negatives),
        },
    }
    return (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode("utf-8")


def render_files(corpus: Corpus) -> dict[str, bytes]:
    cite_rows, negative_rows = _label_rows(corpus)
    files = {
        "README.txt": (ROOT_README + "\n").encode("utf-8"),
        "input/README.txt": (INPUT_README + "\n").encode("utf-8"),
        "input/rfis.csv": _csv(
            INPUT_HEADER,
            [
                [g.rfi.rfi_id, g.rfi.subject, g.rfi.question, g.rfi.response]
                for g in corpus.rfis
            ],
        ),
        "labels/README.txt": (LABELS_README + "\n").encode("utf-8"),
        "labels/citations.csv": _csv(CITATION_HEADER, cite_rows),
        "labels/negatives.csv": _csv(NEGATIVE_HEADER, negative_rows),
        "labels/rfis.csv": _csv(
            RFI_HEADER, [[g.rfi.rfi_id, g.template_id, g.family] for g in corpus.rfis]
        ),
    }
    files["manifest.json"] = _manifest(corpus, files)
    return dict(sorted(files.items()))


class UnsafeOutput(ValueError):
    pass


def _refuse_symlinks(out: Path, names: Iterable[str]) -> None:
    paths = [out, out / "input", out / "labels"]
    paths.extend(out / name for name in names)
    for path in paths:
        if path.is_symlink():
            raise UnsafeOutput(
                f"{path} is a symbolic link. Pick a plain folder for the output "
                "or replace the link with a real folder or file, then run again."
            )


def write_corpus(corpus: Corpus, out: Path) -> None:
    """Write the files of a corpus into out.

    Existing files with the same names are overwritten. The output folder, its
    input and labels folders and every target file must not be symbolic links,
    otherwise UnsafeOutput is raised before anything is written.
    """
    files = render_files(corpus)
    _refuse_symlinks(out, files)
    for name, data in files.items():
        path = out / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
