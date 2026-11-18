from dataclasses import dataclass

from rfikit.synth.rng import Rng

GENERAL_KINDS = (
    "ieee_transactions",
    "rfi_number",
    "kva_rating",
    "room_number",
    "sheet_number",
    "ip_rating",
    "drawing_number",
    "ansi_color",
    "ansi_class",
    "ansi_sheet",
    "astm_grade",
    "part_number",
    "nema_enclosure",
    "nema_plug",
    "nema_size",
    "nema_premium",
    "date",
)
CLAUSE_KINDS = ("bare_rule", "bare_nesc_no_context", "spec_section")
MONTHS = (
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
)


@dataclass(frozen=True)
class NegSpec:
    kind: str
    prefix: str
    text: str
    suffix: str


def _date(rng: Rng) -> str:
    year = rng.between(2018, 2027)
    month = rng.between(1, 12)
    day = rng.between(1, 28)
    shape = rng.below(3)
    if shape == 0:
        return f"{year}-{month:02d}-{day:02d}"
    if shape == 1:
        return f"{month:02d}/{day:02d}/{year}"
    return f"{MONTHS[month - 1]} {day}, {year}"


def make_negative(rng: Rng, kind: str) -> NegSpec:
    if kind == "ieee_transactions":
        return NegSpec(kind, "", "IEEE Transactions", " paper")
    if kind == "rfi_number":
        return NegSpec(kind, "", f"RFI-{rng.between(1, 1999):04d}", "")
    if kind == "kva_rating":
        return NegSpec(kind, "", f"{rng.between(50, 3000)} kVA", " unit")
    if kind == "room_number":
        return NegSpec(kind, "", f"Room {rng.between(100, 399)}", "")
    if kind == "sheet_number":
        number = f"E-{rng.between(100, 399)}-{rng.between(1, 4)}"
        return NegSpec(kind, "sheet ", number, "")
    if kind == "ip_rating":
        return NegSpec(kind, "", f"IP{rng.pick((54, 55, 65, 66, 67))}", " enclosure")
    if kind == "drawing_number":
        number = f"{rng.between(100, 99999)}-{rng.between(1, 9)}"
        return NegSpec(kind, "drawing ", number, "")
    if kind == "ansi_color":
        return NegSpec(kind, "", f"ANSI {rng.pick((49, 61, 70))} gray", " finish")
    if kind == "ansi_class":
        text = f"ANSI Class {rng.pick((150, 300, 600, 900))}"
        return NegSpec(kind, "", text, " flange")
    if kind == "ansi_sheet":
        text = f"ANSI {rng.pick(('B', 'C', 'D', 'E'))} size sheets"
        return NegSpec(kind, "", text, "")
    if kind == "astm_grade":
        return NegSpec(kind, "", rng.pick(("A36", "A53", "A500", "A992")), " steel")
    if kind == "part_number":
        letter = rng.pick(("A", "F", "P"))
        number = f"{letter}{rng.between(100, 999)}-{rng.between(1000, 9999)}"
        return NegSpec(kind, "part ", number, "")
    if kind == "nema_enclosure":
        text = rng.pick(("4X", "3R", "12", "1", "4", "3"))
        return NegSpec(kind, "", f"NEMA {text}", " enclosure")
    if kind == "nema_plug":
        text = rng.pick(("5-15R", "5-20R", "6-20R", "6-50R", "14-30R"))
        return NegSpec(kind, "", f"NEMA {text}", " receptacle")
    if kind == "nema_size":
        return NegSpec(kind, "", f"NEMA Size {rng.between(1, 5)}", " starter")
    if kind == "nema_premium":
        return NegSpec(kind, "", "NEMA Premium", " motor")
    if kind == "date":
        return NegSpec(kind, "dated ", _date(rng), "")
    if kind == "bare_rule":
        return NegSpec(kind, "", f"Rule {rng.between(2, 40)}", " of the contract")
    if kind == "bare_nesc_no_context":
        text = rng.pick(("Rule 232", "Rule 250B", "Rule 234B", "Table 232-1"))
        return NegSpec(kind, "", text, "")
    if kind == "spec_section":
        first = rng.between(3, 48)
        text = f"Section {first:02d} {rng.between(0, 99):02d} {rng.between(0, 99):02d}"
        return NegSpec(kind, "", text, "")
    raise ValueError(f"unknown negative kind: {kind}")
