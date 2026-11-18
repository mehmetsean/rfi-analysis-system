import pytest

from rfikit.cite import CiteContext, extract, extract_rfi, parse_designation
from rfikit.types import Rfi

EN = chr(0x2013)
EM = chr(0x2014)
NB = chr(0xA0)
NNB = chr(0x202F)
ASTRAL = chr(0x1D400)


def run(text: str) -> list[tuple[str, str]]:
    return [(text[c.start : c.end], c.designation.key()) for c in extract(text)]


def keys(text: str) -> list[str]:
    return [key for _, key in run(text)]


BODY_CASES = [
    ("per IEEE C57.12.00-2015 for it", "IEEE C57.12.00-2015", "IEEE C57.12.00-2015"),
    ("IEEE Std 80-2013 applies", "IEEE Std 80-2013", "IEEE 80-2013"),
    ("see IEEE 1547.1 now", "IEEE 1547.1", "IEEE 1547.1"),
    ("see IEEE 1547a-2020.", "IEEE 1547a-2020", "IEEE 1547a-2020"),
    ("IEEE C37.20.2 gear", "IEEE C37.20.2", "IEEE C37.20.2"),
    ("ANSI/IEEE C37.2-2008 relay", "ANSI/IEEE C37.2-2008", "IEEE C37.2-2008"),
    ("IEEE/IEC 1588-2019 time", "IEEE/IEC 1588-2019", "IEEE 1588-2019"),
    ("IEC 60076-1:2011 limits", "IEC 60076-1:2011", "IEC 60076-1:2011"),
    ("IEC 61850 only", "IEC 61850", "IEC 61850"),
    (
        "IEC TS 61850-7-4:2010+AMD1:2020 ok",
        "IEC TS 61850-7-4:2010+AMD1:2020",
        "IEC TS 61850-7-4:2010+AMD1:2020",
    ),
    ("IEC TR 61850-1:2013 ok", "IEC TR 61850-1:2013", "IEC TR 61850-1:2013"),
    (
        "IEC/IEEE 60255-118-1:2018 ok",
        "IEC/IEEE 60255-118-1:2018",
        "IEC 60255-118-1:2018",
    ),
    ("IEC60076-1 ok", "IEC60076-1", "IEC 60076-1"),
    ("ANSI C84.1-2020 voltage", "ANSI C84.1-2020", "ANSI C84.1-2020"),
    ("ANSI Z535.4 signs", "ANSI Z535.4", "ANSI Z535.4"),
    ("ANSI C 84.1 spaced", "ANSI C 84.1", "ANSI C84.1"),
    ("ASTM A123/A123M-17 zinc", "ASTM A123/A123M-17", "ASTM A123/A123M-17"),
    ("ASTM A 123 zinc", "ASTM A 123", "ASTM A123"),
    ("ASTM D2240-15(2021) ok", "ASTM D2240-15(2021)", "ASTM D2240-15(2021)"),
    ("ASTM A153/A153M-16a ok", "ASTM A153/A153M-16a", "ASTM A153/A153M-16a"),
    ("ASTM D1557-12e1 ok", "ASTM D1557-12e1", "ASTM D1557-12e1"),
    ("ASTM B117 salt", "ASTM B117", "ASTM B117"),
    ("NEMA TC 2-2020 conduit", "NEMA TC 2-2020", "NEMA TC 2-2020"),
    ("NEMA 250-2018 enclosures", "NEMA 250-2018", "NEMA 250-2018"),
    ("NEMA ICS 6 ok", "NEMA ICS 6", "NEMA ICS 6"),
    ("ANSI/NEMA MG 1-2016 motor", "ANSI/NEMA MG 1-2016", "NEMA MG 1-2016"),
    ("the NESC applies", "NESC", "NESC"),
    ("the 2017 NESC applies", "2017 NESC", "NESC 2017"),
    ("under NESC-2017 here", "NESC-2017", "NESC 2017"),
    ("under NESC 2012 here", "NESC 2012", "NESC 2012"),
    ("IEEE C2-2017 here", "IEEE C2-2017", "NESC 2017"),
    ("ANSI C2-2017 here", "ANSI C2-2017", "NESC 2017"),
    ("ANSI/IEEE C2-2017 here", "ANSI/IEEE C2-2017", "NESC 2017"),
    ("IEEE C2 here", "IEEE C2", "NESC"),
    ("ANSI C2 here", "ANSI C2", "NESC"),
]


@pytest.mark.parametrize(("text", "span", "key"), BODY_CASES)
def test_positive_case(text: str, span: str, key: str) -> None:
    assert run(text) == [(span, key)]


HARD_NEGATIVES = [
    "IEEE Transactions paper",
    "see RFI-1547 for it",
    "the 1547 kVA unit",
    "Room 232 is small",
    "sheet E-232-1 shows it",
    "IP65 enclosure",
    "drawing 60076-1 is old",
    "ANSI 61 gray finish",
    "ANSI Class 150 flange",
    "ANSI D size sheets",
    "A36 steel plate",
    "ASTM grade steel",
    "part A123-4567 is a bolt",
    "NEMA 4X enclosure",
    "NEMA 3R enclosure",
    "NEMA 12 enclosure",
    "NEMA 5-20R receptacle",
    "NEMA 14-30R receptacle",
    "NEMA Size 2 starter",
    "NEMA Premium motor",
    "dated 2017-06-01 here",
    "dated 06/12/2019 here",
    "dated March 4, 2019 here",
    "Rule 12 of the contract",
    "Rule 232 with no code",
    "Table 232-1 with no code",
    "Section 26 05 26 covers it",
    "IEE 1547 misspelled",
    "ASMT A36 misspelled",
    "IEC 6O076-1 letter O",
    "NSEC Rule 232",
    "IEEEE 80 misspelled",
    "xIEEE 80 glued",
    "IEEE",
    "IEC",
    "ANSI",
    "ASTM",
    "NEMA",
    "IEEE Std",
    "",
]


@pytest.mark.parametrize("text", HARD_NEGATIVES)
def test_hard_negative(text: str) -> None:
    assert run(text) == []


OUT_OF_SCOPE = [
    "ANSI/TIA-568-D wiring",
    "ANSI/TIA 568-D wiring",
    "ANSI/ISA 84.00.01 safety",
    "ANSI/ASME B16.5 flange",
    "ANSI/NFPA 70E arc flash",
    "ANSI/UL 1741 inverter",
    "NFPA 70 code",
    "UL 489 breaker",
    "CSA Z462 work",
    "EN 50160 voltage",
]


@pytest.mark.parametrize("text", OUT_OF_SCOPE)
def test_out_of_scope_emits_nothing(text: str) -> None:
    assert run(text) == []


def test_ansi_joined_to_out_body_does_not_hide_next_citation() -> None:
    assert run("ANSI/NFPA 70E and IEEE 80-2013") == [("IEEE 80-2013", "IEEE 80-2013")]


def test_precedence_c2_is_nesc() -> None:
    cites = extract("IEEE C2-2017")
    assert cites[0].designation.body == "NESC"
    assert cites[0].designation.co_bodies == ("IEEE",)
    assert cites[0].designation.year == "2017"


def test_precedence_first_developing_body() -> None:
    ansi = extract("ANSI/IEEE C37.2")[0].designation
    assert (ansi.body, ansi.co_bodies) == ("IEEE", ("ANSI",))
    iec = extract("IEC/IEEE 60255-118-1:2018")[0].designation
    assert (iec.body, iec.co_bodies) == ("IEC", ("IEEE",))
    ieee = extract("IEEE/IEC 1588")[0].designation
    assert (ieee.body, ieee.co_bodies) == ("IEEE", ("IEC",))


def test_same_key_with_and_without_ansi() -> None:
    assert keys("ANSI/IEEE C37.2") == keys("IEEE C37.2")


def test_scan_resumes_at_end_of_match() -> None:
    assert run("IEEE 80-2013 IEEE 81-2012") == [
        ("IEEE 80-2013", "IEEE 80-2013"),
        ("IEEE 81-2012", "IEEE 81-2012"),
    ]


CLAUSES = [
    ("Section 5.3 of IEEE 80", "IEEE 80 Clause 5.3"),
    ("Table 3 in IEEE 80-2013", "IEEE 80-2013 Table 3"),
    ("IEEE 80-2013, Section 5.3", "IEEE 80-2013 Clause 5.3"),
    ("IEEE 80-2013 Sec. 5.3", "IEEE 80-2013 Clause 5.3"),
    ("IEEE 80, para 4.2.1", "IEEE 80 Clause 4.2.1"),
    ("IEEE 80, Figure 2", "IEEE 80 Figure 2"),
    ("IEEE 80, Annex B", "IEEE 80 Annex B"),
    ("IEEE 80, Clause 6", "IEEE 80 Clause 6"),
    ("IEEE 80, Rule 7", "IEEE 80 Rule 7"),
    ("NESC Rule 232B1", "NESC Rule 232B1"),
    ("2017 NESC Rule 232B1", "NESC 2017 Rule 232B1"),
    ("NESC Table 232-1", "NESC Table 232-1"),
    ("NESC Sec. 9", "NESC Section 9"),
    ("NESC Section 23", "NESC Section 23"),
    ("Rule 232B1 of the NESC", "NESC Rule 232B1"),
    ("Section 9 of the 2017 NESC", "NESC 2017 Section 9"),
    ("rule 234B1a of the nesc", "NESC Rule 234B1a"),
]


@pytest.mark.parametrize(("text", "key"), CLAUSES)
def test_clause_key(text: str, key: str) -> None:
    assert keys(text) == [key]


def test_clause_offsets_and_span_stay_apart() -> None:
    text = "per 2017 NESC Rule 232B1 today"
    cite = extract(text)[0]
    assert text[cite.start : cite.end] == "2017 NESC"
    assert cite.clause_start is not None and cite.clause_end is not None
    assert text[cite.clause_start : cite.clause_end] == "Rule 232B1"
    assert cite.designation.base_key() == "NESC Rule 232B1"


def test_clause_before_binds_forward_not_back() -> None:
    text = "IEEE 80, Table 3 in IEEE 81"
    assert keys(text) == ["IEEE 80", "IEEE 81 Table 3"]


def test_clause_with_of_something_else_stays_unbound() -> None:
    assert keys("IEEE 80 Section 5 of the contract") == ["IEEE 80"]


def test_clause_too_far_is_not_attached() -> None:
    gap = "x" * 45
    assert keys("IEEE 80 " + gap + " Section 5") == ["IEEE 80"]
    near = "x" * 30
    assert keys("IEEE 80 " + near + " Section 5") == ["IEEE 80 Clause 5"]


def test_clause_belongs_to_one_citation() -> None:
    assert keys("IEEE 80, Section 5, IEEE 81") == ["IEEE 80 Clause 5", "IEEE 81"]
    assert keys("Section 5 of IEEE 80, Table 3") == ["IEEE 80 Clause 5"]


def test_nearest_preceding_takes_the_clause() -> None:
    assert keys("IEEE 80 and IEEE 81, Section 5") == ["IEEE 80", "IEEE 81 Clause 5"]


def test_spec_section_is_not_a_clause() -> None:
    assert keys("IEEE 80 Section 26 05 26") == ["IEEE 80"]


def test_clause_without_designation_is_dropped() -> None:
    assert run("see Section 5.3 of the plan") == []


def test_list_continuation() -> None:
    text = "IEEE C57.12.00, C57.12.90 and C57.91"
    cites = extract(text)
    assert [text[c.start : c.end] for c in cites] == [
        "IEEE C57.12.00",
        "C57.12.90",
        "C57.91",
    ]
    assert [c.designation.key() for c in cites] == [
        "IEEE C57.12.00",
        "IEEE C57.12.90",
        "IEEE C57.91",
    ]
    assert [c.inferred for c in cites] == [False, True, True]


def test_list_items_keep_year_and_other_bodies() -> None:
    assert keys("ASTM A123/A123M-17, A36 and B117-19") == [
        "ASTM A123/A123M-17",
        "ASTM A36",
        "ASTM B117-19",
    ]
    assert keys("IEC 60076-1:2011, 60076-2 and 60076-3") == [
        "IEC 60076-1:2011",
        "IEC 60076-2",
        "IEC 60076-3",
    ]
    assert keys("NEMA TC 2, TC 3, and MG 1") == ["NEMA TC 2", "NEMA TC 3", "NEMA MG 1"]
    assert keys("ANSI C84.1, C12.20") == ["ANSI C84.1", "ANSI C12.20"]


def test_list_stops_at_plain_number_and_units() -> None:
    assert keys("IEEE 1547, 2500 kVA and 34.5 kV") == ["IEEE 1547"]
    assert keys("IEEE 80, 81 and 82") == ["IEEE 80"]
    assert keys("IEC 60076-1, 12345 kV") == ["IEC 60076-1"]
    assert keys("IEEE 1547, 2017 NESC") == ["IEEE 1547", "NESC 2017"]


def test_list_stops_at_units_on_the_next_line() -> None:
    assert keys("IEEE C57.12.00, C57\nkVA rating") == ["IEEE C57.12.00"]
    assert keys("ANSI C84.1, C12\r\nkV") == ["ANSI C84.1"]
    assert keys("IEEE C57.12.00, C2\nNESC Rule 232") == [
        "IEEE C57.12.00",
        "NESC Rule 232",
    ]


def test_clause_after_list_binds_last_item() -> None:
    assert keys("IEEE C57.12.00 and C57.91, Section 4") == [
        "IEEE C57.12.00",
        "IEEE C57.91 Clause 4",
    ]


FAR = " " + "x" * 45 + " "


def test_bare_nesc_needs_context() -> None:
    assert run("Rule 232B1 and Table 232-1 apply") == []
    text = "The NESC governs." + FAR + "Rule 232B1 and Table 232-1 apply."
    cites = extract(text)
    assert [c.designation.key() for c in cites] == [
        "NESC",
        "NESC Rule 232B1",
        "NESC Table 232-1",
    ]
    assert [c.inferred for c in cites] == [False, True, True]
    bare = cites[1]
    assert (bare.start, bare.end) == (bare.clause_start, bare.clause_end)
    assert text[bare.start : bare.end] == "Rule 232B1"


def test_clause_near_nesc_is_not_bare() -> None:
    cites = extract("The NESC governs. Rule 232B1 and Table 232-1 apply.")
    assert [c.designation.key() for c in cites] == [
        "NESC Rule 232B1",
        "NESC Table 232-1",
    ]
    assert [c.inferred for c in cites] == [False, True]


def test_bare_nesc_has_no_edition() -> None:
    text = "2017 NESC. 2012 NESC." + FAR + "Rule 234B."
    assert keys(text) == ["NESC 2017", "NESC 2012", "NESC Rule 234B"]


def test_bare_nesc_skips_short_ids() -> None:
    assert keys("The NESC governs." + FAR + "Rule 12 of the contract.") == ["NESC"]
    assert keys("The NESC governs." + FAR + "Section 5.3 of the plan.") == ["NESC"]


def test_bare_nesc_context_across_columns() -> None:
    rfi = Rfi("R-1", "Rule 232B1 question", "Which NESC edition?", "Use Table 232-1")
    cites = extract_rfi(rfi)
    assert [(c.column, c.designation.key()) for c in cites] == [
        ("subject", "NESC Rule 232B1"),
        ("question", "NESC"),
        ("response", "NESC Table 232-1"),
    ]
    quiet = Rfi("R-2", "Rule 232B1 question", "No code named", "")
    assert extract_rfi(quiet) == []


def test_context_argument() -> None:
    assert keys("Rule 232B1") == []
    on = extract("Rule 232B1", context=CiteContext(nesc=True))
    assert [c.designation.key() for c in on] == ["NESC Rule 232B1"]
    off = extract("NESC Rule 232B1", context=CiteContext(nesc=False))
    assert [c.designation.key() for c in off] == ["NESC Rule 232B1"]


def test_column_is_recorded() -> None:
    assert extract("IEEE 80", column="question")[0].column == "question"


BREAK_CASES = [
    ("IEEE\nC57.12.00-2015", "IEEE C57.12.00-2015"),
    ("IEEE\r\n  C57.12.00-2015", "IEEE C57.12.00-2015"),
    ("IEEE C57.12.\n00-2015", "IEEE C57.12.00-2015"),
    ("IEEE C57.\r\n12.00-2015", "IEEE C57.12.00-2015"),
    ("IEEE C57.12.00-\n2015", "IEEE C57.12.00-2015"),
    ("IEC 60076-\n1:2011", "IEC 60076-1:2011"),
    ("IEC\n60076-1:2011", "IEC 60076-1:2011"),
    ("IEC 61850-7-\r\n4:2010", "IEC 61850-7-4:2010"),
    ("ASTM\nA123/A123M-17", "ASTM A123/A123M-17"),
    ("ASTM A123/A123M-\n17", "ASTM A123/A123M-17"),
    ("NEMA\n  TC 2-2020", "NEMA TC 2-2020"),
    ("NEMA TC 2-\n2020", "NEMA TC 2-2020"),
    ("ANSI\nC84.1-2020", "ANSI C84.1-2020"),
    ("ANSI C84.\n1-2020", "ANSI C84.1-2020"),
    ("NESC-\n2017", "NESC 2017"),
]


@pytest.mark.parametrize(("text", "key"), BREAK_CASES)
def test_line_break_inside_designation(text: str, key: str) -> None:
    assert run(text) == [(text, key)]


def test_line_break_after_designation_is_not_swallowed() -> None:
    text = "IEEE 80-2013\nThe next line"
    assert run(text) == [("IEEE 80-2013", "IEEE 80-2013")]


def test_en_and_em_dash_from_escapes() -> None:
    assert run("IEEE 80" + EN + "2013") == [("IEEE 80" + EN + "2013", "IEEE 80-2013")]
    assert run("IEEE 80" + EM + "2013") == [("IEEE 80" + EM + "2013", "IEEE 80-2013")]
    assert keys("IEC 60076" + EN + "1:2011") == ["IEC 60076-1:2011"]
    assert keys("ASTM A123/A123M" + EM + "17") == ["ASTM A123/A123M-17"]
    assert keys("NESC" + EN + "2017") == ["NESC 2017"]
    assert keys("IEEE C2" + EM + "2017") == ["NESC 2017"]


def test_unicode_dash_range_is_covered() -> None:
    for code in (0x2010, 0x2011, 0x2012, 0x2013, 0x2014, 0x2015, 0x2212):
        assert keys("IEEE 80" + chr(code) + "2013") == ["IEEE 80-2013"]


def test_no_break_spaces() -> None:
    assert run("IEEE" + NB + "80-2013") == [("IEEE" + NB + "80-2013", "IEEE 80-2013")]
    assert keys("ANSI" + NNB + "C84.1") == ["ANSI C84.1"]
    assert keys("NEMA" + NB + "TC" + NNB + "2") == ["NEMA TC 2"]


def test_spacing_and_case() -> None:
    assert keys("IEEE  80-2013") == ["IEEE 80-2013"]
    assert keys("IEEE80-2013") == ["IEEE 80-2013"]
    assert keys("ASTM A123/A123M-17") == keys("ASTM  A 123/A123M-17")
    assert keys("ieee std c57.12.00-2015") == ["IEEE C57.12.00-2015"]
    assert keys("Ieee 80") == ["IEEE 80"]
    assert keys("Nema MG 1") == ["NEMA MG 1"]
    assert keys("nema tc 2-2020") == ["NEMA TC 2-2020"]
    assert keys("astm a123/a123m-17") == ["ASTM A123/A123M-17"]
    assert keys("iec ts 61850-7-4:2010") == ["IEC TS 61850-7-4:2010"]
    assert keys("the nesc and ansi c84.1") == ["NESC", "ANSI C84.1"]


def test_lowercase_words_are_not_designations() -> None:
    assert run("nema to 3 places") == []
    assert run("astm a 3 points") == []
    assert run("NEMA is 3 places") == []


def test_astral_character_before_citation() -> None:
    text = ASTRAL + ASTRAL + " IEEE 80-2013"
    cite = extract(text)[0]
    assert (cite.start, cite.end) == (3, 15)
    assert text[cite.start : cite.end] == "IEEE 80-2013"


def test_text_is_the_original_slice() -> None:
    text = "IEEE" + NB + "80" + EN + "2013"
    assert extract(text)[0].text == text


def test_key_formats() -> None:
    cite = extract("IEEE 80-2013 Section 5.3")[0]
    assert cite.designation.key() == "IEEE 80-2013 Clause 5.3"
    assert cite.designation.base_key() == "IEEE 80"
    iec = extract("IEC TS 61850-7-4:2010+AMD1:2020")[0].designation
    assert iec.base_key() == "IEC TS 61850-7-4"
    astm = extract("ASTM A153/A153M-16a")[0].designation
    assert astm.base_key() == "ASTM A153/A153M"
    assert (astm.number, astm.year, astm.suffix) == ("A153/A153M", "16", "a")
    nema = extract("NEMA TC 2-2020")[0].designation
    assert (nema.number, nema.year) == ("TC 2", "2020")
    nesc = extract("the 2017 NESC Rule 232B1")[0].designation
    assert (nesc.number, nesc.year, nesc.clause) == ("C2", "2017", "Rule 232B1")


def test_parse_designation() -> None:
    parsed = parse_designation("  ASTM A123/A123M-17 ")
    assert parsed is not None and parsed.key() == "ASTM A123/A123M-17"
    clause = parse_designation("IEEE 80-2013, Section 5.3")
    assert clause is not None and clause.key() == "IEEE 80-2013 Clause 5.3"
    assert parse_designation("see IEEE 80") is None
    assert parse_designation("IEEE 80 and more") is None
    assert parse_designation("IEEE Transactions") is None
    assert parse_designation("") is None


def test_extract_orders_by_start() -> None:
    text = "Rule 232B1 of the NESC and IEEE 80 and Table 232-1"
    starts = [c.start for c in extract(text)]
    assert starts == sorted(starts)


def test_and_or_between_starts_a_new_item() -> None:
    text = "The list has NESC and Rule 232B2 next."
    cites = extract(text)
    assert [c.designation.key() for c in cites] == ["NESC", "NESC Rule 232B2"]
    assert [c.inferred for c in cites] == [False, True]
    assert keys("IEEE 80 or Table 3 here") == ["IEEE 80"]


def test_out_of_scope_body_is_not_a_nema_list_item() -> None:
    assert keys("NEMA MG 1 and UL 489") == ["NEMA MG 1"]
    assert keys("NEMA MG 1, EN 50160") == ["NEMA MG 1"]


def test_clause_of_something_else_is_not_bare_nesc() -> None:
    text = "The NESC governs." + FAR + "Rule 232B1 of the design."
    assert keys(text) == ["NESC"]


def test_misspelled_neighbor_can_take_a_clause() -> None:
    text = "IEEE 80-2013 with IEE 81, Table 7"
    assert keys(text) == ["IEEE 80-2013 Table 7"]


UNIT_KEEP = [
    "See IEEE C57.12.00, C57.12.90\nA copy is attached.",
    "IEEE C57.12.00 and C57.12.91 a test is required",
]
UNIT_DROP = [
    "IEEE C57.12.00, C57\nkVA rating",
    "ANSI C84.1, C12\r\nkV",
    "IEEE C57.12.00, C57 V rating",
]


@pytest.mark.parametrize("text", UNIT_KEEP)
def test_single_letter_word_after_item_is_not_a_unit(text: str) -> None:
    assert len(keys(text)) == 2


@pytest.mark.parametrize("text", UNIT_DROP)
def test_unit_after_item_drops_the_item(text: str) -> None:
    assert len(keys(text)) == 1


def test_nesc_on_next_line_is_not_a_list_item() -> None:
    text = "IEEE C57.12.00, C2\nNESC Rule 232"
    assert keys(text) == ["IEEE C57.12.00", "NESC Rule 232"]


def test_clause_reach_is_forty_characters() -> None:
    assert keys("IEEE 80" + " " * 40 + "Table 3") == ["IEEE 80 Table 3"]
    assert keys("IEEE 80" + " " * 41 + "Table 3") == ["IEEE 80"]


def test_clause_number_with_trailing_digits_is_rejected() -> None:
    assert keys("NESC Table 232-12345") == ["NESC"]
    assert keys("IEEE 80 Table 3-12345") == ["IEEE 80"]


def test_nesc_table_needs_one_or_two_digits_after_the_dash() -> None:
    assert keys("The NESC governs." + FAR + "Table 232-12") == [
        "NESC",
        "NESC Table 232-12",
    ]
    assert keys("The NESC governs." + FAR + "Table 232-123") == ["NESC"]


def test_clause_word_inside_a_designation_is_not_a_clause() -> None:
    assert keys("IEEE 80 NEMA SEC 5") == ["IEEE 80", "NEMA SEC 5"]


def test_second_nesc_does_not_reuse_the_year_before_the_first() -> None:
    assert keys("NESC 2017 NESC") == ["NESC 2017", "NESC"]
    assert keys("2017 NESC 2018 NESC") == ["NESC 2018", "NESC"]


def test_list_continuation_does_not_cross_a_line_break() -> None:
    assert keys("IEEE C57.12.00,\nC57.12.90") == ["IEEE C57.12.00"]


BREAKS = [chr(0x85), chr(0x2028), chr(0x2029)]


@pytest.mark.parametrize("brk", BREAKS)
def test_unicode_break_inside_a_designation(brk: str) -> None:
    assert keys("IEEE" + brk + "C57.12.00") == ["IEEE C57.12.00"]


@pytest.mark.parametrize("brk", BREAKS)
def test_unicode_break_before_a_clause_connector(brk: str) -> None:
    assert keys("Table 3" + brk + "of IEEE 80") == ["IEEE 80 Table 3"]


def test_longest_designation_needs_the_whole_window() -> None:
    gap = "-\r\n    123"
    text = "IEC" + " " * 6 + "Std." + " " * 6 + "TS" + " " * 6 + "12345"
    text += gap * 4 + ":2011+AMD12:2011"
    assert keys(text) == ["IEC TS 12345-123-123-123-123:2011+AMD12:2011"]
