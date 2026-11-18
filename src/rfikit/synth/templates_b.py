from rfikit.synth.templates import Template

TEMPLATES_B = (
    Template(
        "dc-B1",
        "B",
        "design_clarification",
        "Design intent question, {i1}, {p1}",
        "{g}From {r1}: at the {d1}, the {i1} appears under {c1}, and a second sheet "
        "points to {c2}. Which of the two reflects the design intent? "
        "Detail ref {x1}.",
        "Answered by {r2}: see the addendum.",
    ),
    Template(
        "mi-B1",
        "B",
        "missing_information",
        "{p1}: incomplete reference for the {i1}",
        "{g}Ref {k1}. Nothing in the {d1} package gives the year for {y1}, and the "
        "list for the {i1} stops short. Please issue the missing year and the "
        "rest of the list.",
        "{r1}: Issued with the next bulletin.",
    ),
    Template(
        "cf-B1",
        "B",
        "document_conflict",
        "Two sources, one {i1}, {p1}",
        "{g}{r1} found that the owner list says {e1} and the vendor data says "
        "{e2} for the {i1}. These cannot both stand. Please decide which source "
        "governs. Ref {x1}.",
        "{r2}: The owner will answer.",
    ),
    Template(
        "sr-B1",
        "B",
        "substitution_request",
        "{p1} alternate for the {i1}",
        "{g}Can the contractor swap {w1} for {c1} on the {i1}? The swap is "
        "offered at no cost to the owner. Ref {x1}.",
        "{r1}: Swap accepted. We also list {o1} on the cover sheet.",
    ),
    Template(
        "fc-B1",
        "B",
        "field_condition",
        "{p1} site finding, {a1}",
        "{g}On site, {r1} reports that the {i1} is damaged and the field layout "
        "is not the layout on paper. The paper layout leans on {c1} and {o1}. "
        "Please give direction. Note {x1}.",
        "{r2}: A visit is set for this week.",
    ),
    Template(
        "sa-B1",
        "B",
        "standard_applicability",
        "Scope check for {p1}",
        "{g}We want to know if {c1} reaches the {i1} in the {d1} scope, or only "
        "the larger equipment. Please confirm. Ref {x1}.",
        "{r1}: Noted for the next review.",
    ),
)
