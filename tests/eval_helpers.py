import csv
from pathlib import Path

from rfikit.evaluate import (
    CITATION_HEADER,
    INPUT_HEADER,
    NEGATIVE_HEADER,
    RFI_HEADER,
)

W1_Q = (
    "Use IEEE C57.12.00-2015, Section 5.3 and ASTM A123/A123M-17 here. "
    "Room 232 is closed. NFPA 70E applies."
)
W2_Q = (
    "Check IEE 1547 and IEC 60076-1:2011. Also ASTM E119, IEC 61850 and "
    "NEMA 4X. Add ANSI/TIA-568 too."
)


def at(text: str, part: str) -> tuple[int, int]:
    start = text.index(part)
    return start, start + len(part)


def cite(
    rfi_id: str,
    text: str,
    part: str,
    key: str,
    base: str,
    clause: str = "",
    scope: str = "in",
    noise: str = "",
) -> list[str]:
    start, end = at(text, part)
    c_start = c_end = ""
    if clause:
        a, b = at(text, clause)
        c_start, c_end = str(a), str(b)
    return [
        rfi_id,
        "question",
        str(start),
        str(end),
        c_start,
        c_end,
        key,
        base,
        scope,
        "0",
        "real",
        noise,
    ]


def negative(rfi_id: str, text: str, part: str, kind: str) -> list[str]:
    start, end = at(text, part)
    return [rfi_id, "question", str(start), str(end), kind]


def write_rows(path: Path, header: tuple[str, ...], rows: list[list[str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(header)
        writer.writerows(rows)


def make_folder(root: Path, second_family: str = "B") -> Path:
    write_rows(
        root / "input" / "rfis.csv",
        INPUT_HEADER,
        [["W1", "First", W1_Q, ""], ["W2", "Second", W2_Q, ""]],
    )
    write_rows(
        root / "labels" / "rfis.csv",
        RFI_HEADER,
        [
            ["W1", "design_clarification", "single-W1", "", "A"],
            ["W2", "design_clarification", "single-W2", "", second_family],
        ],
    )
    write_rows(
        root / "labels" / "citations.csv",
        CITATION_HEADER,
        [
            cite(
                "W1",
                W1_Q,
                "IEEE C57.12.00-2015",
                "IEEE C57.12.00-2015 Clause 5.3",
                "IEEE C57.12.00",
                "Section 5.3",
            ),
            cite(
                "W1",
                W1_Q,
                "ASTM A123/A123M-17",
                "ASTM A123/A123M-17",
                "ASTM A123/A123M",
            ),
            cite("W1", W1_Q, "NFPA 70E", "NFPA 70E", "NFPA 70E", scope="out"),
            cite("W2", W2_Q, "IEE 1547", "IEEE 1547", "IEEE 1547", noise="misspelled"),
            cite("W2", W2_Q, "IEC 60076-1:2011", "IEC 60076-1:2011", "IEC 60076-1"),
            cite("W2", W2_Q, "IEC 61850", "IEC 61850", "IEC 61850", scope="out"),
            cite("W2", W2_Q, "ANSI/TIA-568", "TIA 568", "TIA 568", scope="out"),
        ],
    )
    write_rows(
        root / "labels" / "negatives.csv",
        NEGATIVE_HEADER,
        [
            negative("W1", W1_Q, "Room 232", "room_number"),
            negative("W2", W2_Q, "NEMA 4X", "nema_enclosure"),
        ],
    )
    return root
