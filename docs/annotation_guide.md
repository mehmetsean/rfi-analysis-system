# Annotation guide for the written held-out set

This guide is the rulebook for labeling the RFIs in heldout/. One annotator follows it. The synthetic data generator in rfikit.synth writes labels in this same layout. The rules below were written for the written set and the generator follows them.

This is synthetic data, written by hand. Only designations and clause numbers appear, never titles or standard text (see ADR 0003).

## Files and columns

- input/rfis.csv: rfi_id, subject, question, response.
- labels/citations.csv: rfi_id, column, start, end, clause_start, clause_end, key, base_key, scope, inferred, catalog, noise_class.
- labels/negatives.csv: rfi_id, column, start, end, kind.
- labels/rfis.csv: rfi_id, issue_type, group_id, template_id, family. For the written set template_id is empty and family is "written".
- column is one of subject, question, response.
- Offsets count Unicode code points (Python string indices) in the column text as stored in the CSV, start inclusive, end exclusive. clause_start and clause_end are empty when there is no clause.
- inferred is 0 or 1. scope is "in" or "out". catalog is "real" or "invented" (see "The catalog column").

## What is a citation

A citation is a written reference to a document of one of six bodies: IEEE, NESC, IEC, ANSI, ASTM, NEMA. Label it when a reader could look the document up from the text alone. Only the NESC has a key form for the body name alone ("the NESC edition" is a citation with key "NESC"). The name of any other body alone is not a citation. A number with no body is not a citation, except a list continuation or a bare NESC rule or table (below).

## Span convention (ADR 0004)

- The span covers the designation only. It starts at the first character of the body token and ends at the last character of the number, part, year or suffix.
- For a list item the span starts at the first character of the number.
- When the edition comes first ("2017 NESC"), the span starts at the edition.
- "NESC-2017" and "C2-2017" ("IEEE C2-2017", "ANSI C2-2017") are spanned as one whole token.
- "IEEE Std" is part of the body token: the span of "IEEE Std 80-2013" starts at "IEEE".
- A clause has its own clause_start and clause_end. The clause range covers the keyword and the id ("Rule 232B1", "Section 5.3"). A clause never counts in the span.
- An inferred bare NESC rule or table has no designation text, so its clause offsets are its span.
- A line break (\n or \r\n) or spaces inside a designation are inside the span.
- The span never starts or ends with a space.

Example: in "2017 NESC Rule 232B1" the span is "2017 NESC", the clause is "Rule 232B1", the key is "NESC 2017 Rule 232B1" and the base key is "NESC Rule 232B1".

Text pasted from an equation editor can hold characters above U+FFFF, such as the math italic letters in W085. Offsets count code points, so such a character is one position.

## Keys

Keys are written by hand in the style that rfikit.types.Designation.key() and base_key() print. No parser produced them. tests/test_heldout_set.py checks that each key agrees with the labeled text (test_key_matches_slice), that each base key follows the stated rule (test_base_key_rule) and that clause keywords match (test_clause_matches_key). Keys never include co-bodies.

| Body | Key | Base key |
|---|---|---|
| IEEE | IEEE C57.12.00-2015 | IEEE C57.12.00 |
| IEEE amendment | IEEE 1547a-2020 | IEEE 1547a |
| NESC | NESC 2017 Rule 232B1 | NESC Rule 232B1 |
| NESC, no clause | NESC 2017 | NESC |
| NESC, nothing at all | NESC | NESC |
| IEC | IEC 60076-1:2011 | IEC 60076-1 |
| IEC with type and suffix | IEC TS 61850-7-4:2010+AMD1:2020 | IEC TS 61850-7-4 |
| ANSI | ANSI C84.1-2020 | ANSI C84.1 |
| ASTM | ASTM A123/A123M-17 | ASTM A123/A123M |
| ASTM with revision letter | ASTM A153/A153M-16a | ASTM A153/A153M |
| ASTM with reapproval | ASTM D2240-15(2021) | ASTM D2240 |
| NEMA | NEMA TC 2-2020 | NEMA TC 2 |
| NEMA, three digits | NEMA 250-2018 | NEMA 250 |

Key rules:
- Body names and the letters of a number are upper case. A trailing amendment or revision letter and an "e" suffix stay lower case (1547a, 16a, 12e1).
- Spaces inside a number are dropped ("ASTM A 123" is "ASTM A123", "C 84.1" is "C84.1"). Inside NEMA letters and number the single space stays ("TC 2").
- Dashes are ASCII. An IEC year follows a colon, every other body a hyphen. ASTM years keep the two digits as written.
- The document type (TS, TR) is kept for IEC only and comes right after the body.
- A line break or no-break space inside a designation is read as one space or nothing, as the grammar needs.
- A misspelled body or a letter O written for zero is labeled with the key of the document the writer meant.
- Clause in a key: for NESC the keyword is kept (Rule 232B1, Table 232-1, Section 9; "Sec." becomes "Section"). For every other body the keyword is normalized: section, sec., para and clause become "Clause", and table, figure, annex and rule become "Table", "Figure", "Annex" and "Rule". The id is copied as written, spaces removed. So "Section 5.3 of IEEE 80" is "IEEE 80 Clause 5.3".
- A bare NESC rule or table (inferred) has no edition: "NESC Rule 234B".

## Clauses

- A clause is one of: clause, section, sec., para, table, figure, annex or rule, plus an id.
- It belongs to the designation when the id follows within 40 characters of the end of the designation ("IEEE 80-2013, Section 5.3").
- It also belongs when it comes before and is followed by "of" or "in" and then the body ("Section 5.3 of IEEE 80", "Rule 232B1 of the NESC").
- A clause followed by "of" or "in" binds forward. Otherwise the nearest preceding designation within 40 characters takes it.
- A clause belongs to at most one citation.
- A clause with no designation to attach to is not labeled.

## Precedence for joint and alias forms

Apply in this order.

1. C2 after IEEE, ANSI or IEEE/ANSI is NESC. The edition comes from the year ("IEEE C2-2017" is NESC 2017, key "NESC 2017").
2. ANSI joined to a body outside the six (ANSI/TIA, ANSI/ISA, ANSI/ASME, ANSI/UL, ANSI/NFPA) is out of scope. Label it with scope "out" and the key of the other body.
3. Otherwise the first developing body written is the body, and the rest, ANSI included, are co-bodies that never show in a key. ANSI/IEEE C37.2-2008 is "IEEE C37.2-2008". ANSI/NEMA MG 1-2016 is "NEMA MG 1-2016". IEC/IEEE 60255-118-1:2018 is "IEC 60255-118-1:2018". IEEE/IEC 1588-2019 is "IEEE 1588-2019".
4. Labels never overlap. After one match, the next starts where it ended.

The span of a joint form covers the whole joint token, from the first body character to the last character of the number.

## The inferred flag

inferred is 1 for the two cases below and 0 otherwise.
- A list continuation item. In "IEEE C57.12.00, C57.12.90 and C57.91" the second and third items inherit the body when their number fits the body's form. The noise_class of such an item is list_continuation.
- A number followed by a unit (kVA, kV, A, ft and so on) is never a list continuation item. In "IEEE 1547, 2500 kVA and 34.5 kV" only IEEE 1547 is a citation, and "2500 kVA" is a negative of kind kva_rating.
- A bare NESC Rule or Table when NESC is cited elsewhere in the same RFI (subject, question or response count as one RFI). It takes its clause offsets as its span. Its noise_class is empty and its key has no edition.

A bare "Rule 232" or "Table 232-1" in an RFI that never cites NESC is not a citation. Label it as a negative of kind bare_nesc_no_context.

## Out-of-scope bodies

NFPA, UL, ASME, ISA, TIA, CSA and EN are not extracted. Label them with scope "out", the span of the designation, and a key made of the body and the number as written ("NFPA 70E", "TIA 568-D"). The base key is the same as the key. Leave clause offsets empty and inferred 0. ANSI joined to one of these bodies is out too. Out-of-scope labels are never misses.

## Hard negatives

A hard negative is text that looks like a citation and is not one. The span covers the shortest text that contains the confusable part, and the word before it when that word is part of the look-alike. Kinds:

| Kind | Example |
|---|---|
| ieee_transactions | IEEE Transactions |
| rfi_number | RFI-1547 |
| kva_rating | 1547 kVA |
| bare_rule | Rule 12 of the contract |
| bare_nesc_no_context | Rule 232 with no NESC anywhere in the RFI |
| room_number | Room 232 |
| sheet_number | sheet E-232-1 (span: E-232-1) |
| ip_rating | IP65 |
| drawing_number | drawing 60076-1 (span: 60076-1) |
| ansi_color | ANSI 61 gray |
| ansi_class | ANSI Class 150 |
| ansi_sheet | ANSI D size sheet |
| astm_grade | A36 without ASTM |
| part_number | part A123-4567 |
| nema_enclosure | NEMA 4X, NEMA 3R |
| nema_plug | NEMA 5-20R |
| nema_size | NEMA Size 2 |
| nema_premium | NEMA Premium |
| date | 2017-06-01, 06/12/2019 |
| spec_section | Section 26 05 26 |

Spans for bare_rule and bare_nesc_no_context are the keyword and id ("Rule 12"). Spans for spec_section include the word "Section". A negative never overlaps an in-scope citation. A plain voltage or length such as "69 kV" or "3 ft" is not labeled, because it does not look like a designation.

## Noise classes

Each in-scope citation has at most one noise class. When more than one applies, take the first in this list.

1. misspelled: the body is misspelled ("IEE 1547", "ASMT A36") or a letter O is written for zero. The label stays in scope with the key of the intended document. For v0.1 these are expected misses.
2. list_continuation: an inferred list item.
3. line_break: a line break (\n or \r\n) inside the designation, between body and number or after "." or "-" inside a number.
4. unicode_dash: a Unicode dash in place of a hyphen. The set uses only U+2010, U+2011, U+2012 and U+2212. The characters U+2013 and U+2014 are never used in this repository, so they are not part of this noise class.
5. spacing: missing or extra spaces ("IEC60076-1", "ASTM A 123", two spaces) and no-break spaces (U+00A0, U+202F).
6. case: the body or the letters of the number are not in the usual case ("ieee 1547", "Nema MG 1").

The source text for the set writes special characters as escapes. The built input CSV holds the real characters.

## The catalog column

The value "real" means the designation was written from knowledge of a published document of that body: in generated data it is a catalog entry, in the written set it is the annotator's judgment. Neither is checked against the standards, and both are identifiers only. The value "invented" means a number that fits the grammar and is not meant to match a published document. For this set the catalog value describes the document, not the edition.
- real: the designation is believed to match a published document of that body, to the annotator's knowledge. Not checked against the standards.
- invented: the number fits the grammar and is not meant to match a published document. When unsure, mark invented.
- A bare NESC rule or table is real only for rule or table numbers the annotator is confident appear in the NESC.

## Issue types

One type per RFI, chosen from the subject and question (a response never decides it). Apply the rules in this order and stop at the first that fits. Each RFI has exactly one answer.

1. substitution_request: the RFI asks approval to replace a specified item or reference with another.
2. field_condition: the RFI reports a condition found on site that differs from the documents.
3. document_conflict: the RFI says that two project documents or sources disagree and asks which governs.
4. missing_information: the RFI says that a needed item (edition, part, number, rating, clause, list) is absent and asks for it. This holds even when the RFI words the request as "which" or "should X apply".
5. standard_applicability: the RFI asks whether a standard applies to something, or which edition of one standard applies, and says nothing is absent or in conflict.
6. design_clarification: anything else, for example a choice between options or between different standards, or the meaning of a design note.

Two documents that cite different editions are a conflict (rule 3). One document that cites a standard with no edition is missing information (rule 4). A question about which of two named standards to follow is design_clarification.

## Recurring groups

- RFIs that are paraphrases of one question share a group_id. A group has two to four members and the same issue type.
- Group ids for recurring questions look like G01. Every other RFI has its own unique group_id, "single-" plus its rfi_id.
- Paraphrases change wording, order and the written style of a citation, so they do not always cite the same text.

## Limits of this set

- One annotator labeled it. There is no agreement measure, so label noise is unknown.
- The author also wrote the grammar that will be scored against it.
- Later label fixes are listed in heldout/CHANGES.md with the reason. The set was committed before any extractor existed, and the history shows it.
