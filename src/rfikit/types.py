from dataclasses import dataclass

BODIES = ("IEEE", "NESC", "IEC", "ANSI", "ASTM", "NEMA")


@dataclass(frozen=True)
class Rfi:
    rfi_id: str
    subject: str
    question: str
    response: str = ""


@dataclass(frozen=True)
class Designation:
    body: str
    number: str
    co_bodies: tuple[str, ...] = ()
    doc_type: str = ""
    part: str = ""
    year: str = ""
    suffix: str = ""
    clause: str = ""

    def base_key(self) -> str:
        # NESC keeps the rule or table, others keep body, number and part
        if self.body == "NESC":
            return _join(["NESC", self.clause])
        head = _join([self.body, self.doc_type, self.number])
        if self.part:
            head += "-" + self.part
        return head

    def key(self) -> str:
        if self.body == "NESC":
            return _join(["NESC", self.year, self.clause])
        text = self.base_key()
        if self.year:
            sep = ":" if self.body == "IEC" else "-"
            text += sep + self.year
        text += self.suffix
        return _join([text, self.clause])


def _join(parts: list[str]) -> str:
    return " ".join(p for p in parts if p)


@dataclass(frozen=True)
class Citation:
    column: str
    start: int
    end: int
    clause_start: int | None
    clause_end: int | None
    text: str
    designation: Designation
    inferred: bool = False
