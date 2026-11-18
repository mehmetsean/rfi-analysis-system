from rfikit.synth.templates import Template

TEMPLATES_A = (
    Template(
        "dc-A1",
        "A",
        "design_clarification",
        "Which standard for the {i1} at the {d1}",
        "{g}On project {p1} the {i1} at the {d1} is shown with notes that point to "
        "{c1} and to {c2}. Please clarify which one the {i1} follows. "
        "For reference see {x1}.",
        "{r1}: The design team will answer in the next bulletin. "
        "We also list {o1} on the cover sheet.",
    ),
    Template(
        "dc-A2",
        "A",
        "design_clarification",
        "Meaning of the general note on {a1}",
        "{g}The general notes on the {a1} drawing set for {p1} list {n1} and {b1} "
        "next to the {i1}. Please explain what the note means for the {i1} at the "
        "{d1}. See also {x1}.",
        "{r1}: The note will be reworded on the next issue.",
    ),
    Template(
        "dc-A3",
        "A",
        "design_clarification",
        "{i1} layout at the {d1}",
        "{g}Ref {k1}. Our layout of the {i1} for {p1} follows {l1}. "
        "Please confirm the layout matches the design intent.",
        "{r1}: Layout confirmed, see {x1}.",
    ),
    Template(
        "mi-A1",
        "A",
        "missing_information",
        "Edition not stated for the {i1}",
        "{g}The specification for {p1} cites {y1} for the {i1} but gives no edition. "
        "Please state the edition to use for the {d1}.",
        "{r1}: The edition will be added by addendum.",
    ),
    Template(
        "mi-A2",
        "A",
        "missing_information",
        "No rating given for the {i1}",
        "{g}Ref {k1}. The {i1} on the {a1} schedule has no rating listed. "
        "The notes cite {y1}. Please send the missing rating for {p1}. See {x1}.",
        "{r1}: The schedule will be reissued.",
    ),
    Template(
        "mi-A3",
        "A",
        "missing_information",
        "Location not listed for the {i1}",
        "{g}The submittal list for {p1} points to {y1} but names no location "
        "inside it. Which location is meant for the {i1}? "
        "Please add the missing reference.",
        "{r1}: See {x1} for the list that was sent.",
    ),
    Template(
        "cf-A1",
        "A",
        "document_conflict",
        "Drawings and specification disagree on the {i1}",
        "{g}On {p1} the drawings cite {e1} for the {i1}, while the specification "
        "cites {e2}. The two documents disagree. Which one governs?",
        "{r1}: The owner will answer. We also list {o1} on the cover sheet.",
    ),
    Template(
        "cf-A2",
        "A",
        "document_conflict",
        "Conflict between {e1} and {e2}",
        "{g}The bid set for {p1} names both references above for the same {i1} at "
        "the {d1}. Please say which document wins. See {x1}.",
        "{r1}: The design team will answer in the next bulletin.",
    ),
    Template(
        "cf-A3",
        "A",
        "document_conflict",
        "Conflicting notes on {a1}",
        "{g}Ref {k1}. On {p1} the sheet note and the spec text name {c1} and "
        "{c2} for the {i1}. These conflict. Please decide which governs the {d1}. "
        "Related: {x1}.",
    ),
    Template(
        "sr-A1",
        "A",
        "substitution_request",
        "Substitution request for the {i1}",
        "{g}The vendor proposes to replace the specified reference {c1} with {c2} on "
        "the {i1} for {p1}. Please approve the substitution.",
        "{r1}: Approved as noted. We also list {o1} on the cover sheet.",
    ),
    Template(
        "sr-A2",
        "A",
        "substitution_request",
        "Request to change the listed reference for the {i1}",
        "{g}We ask approval to supply the {i1} to {c1} instead of the listed "
        "reference, for the {d1} on {p1}. Price and schedule stay the same. See {x1}.",
    ),
    Template(
        "sr-A3",
        "A",
        "substitution_request",
        "Approved equal for the {i1}",
        "{g}Please approve an equal product for the {i1} at the {a1} of {p1}. "
        "The equal is listed to {l1}. Model data: {x1}.",
        "{r1}: Equal accepted.",
    ),
    Template(
        "fc-A1",
        "A",
        "field_condition",
        "Field condition at the {d1}, {a1}",
        "{g}During work on {p1} the crew found the {i1} already in place at the "
        "{a1}. It does not match the drawings. The drawings cite {c1} and {o1}. "
        "How should we proceed? See {x1}.",
        "{r1}: Hold work at the {a1} until the site visit.",
    ),
    Template(
        "fc-A2",
        "A",
        "field_condition",
        "Existing {i1} differs from the plans",
        "{g}The existing {i1} at the {d1} on {p1} is a different size than "
        "shown. The plan notes list {n1} and {b1}. Please advise how to proceed. "
        "Photo log: {x1}.",
        "{r1}: The EOR will visit the {d1}.",
    ),
    Template(
        "fc-A3",
        "A",
        "field_condition",
        "Unexpected condition at {a1}",
        "{g}Digging at the {a1} for {p1} showed soil and cable routing that the "
        "plans do not show. The plans refer to {c1}. Please advise before we continue. "
        "Note {x1}.",
        "{r1}: Photos received.",
    ),
    Template(
        "sa-A1",
        "A",
        "standard_applicability",
        "Applicability question for the {i1}",
        "{g}Please confirm whether {c1} applies to the {i1} at the {d1} on {p1}. "
        "Ref {x1}.",
        "{r1}: We also list {o1} on the cover sheet.",
    ),
    Template(
        "sa-A2",
        "A",
        "standard_applicability",
        "Which edition applies for the {i1}",
        "{g}The vendor can supply the {i1} to {e1} or to {e2}. "
        "Which edition applies to {p1}? Ref {x1}.",
        "{r1}: The specification edition stays.",
    ),
    Template(
        "sa-A3",
        "A",
        "standard_applicability",
        "Applicability question at {a1}",
        "{g}Does {n1} apply to the {i1} crossing at the {a1} on {p1}? "
        "The design team also lists {b1} for the same crossing. "
        "Please confirm. Ref {x1}.",
    ),
)
