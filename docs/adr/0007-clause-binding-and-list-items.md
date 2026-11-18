# 7. Clause binding stops at and or or, and the grammar skips only line breaks

Status: Accepted

## Context

The spec says a clause attaches to the nearest preceding designation within 40 characters. Read literally, "NESC and Rule 232B2" gives the rule to the NESC, although the writer lists two items. The generator labels that Rule as a bare NESC rule. A second case: a clause followed by "of" or "in" belongs to what follows, so "Rule 12 of the contract" must not take a designation before it.

## Decision

- A clause binds backward only when the text between the designation and the clause holds no word "and" or "or", and the gap is at most 40 characters.
- A clause followed by "of" or "in" (and optionally "the") binds forward only, to a designation that starts right after. If none does, the clause stays unattached and is not a bare NESC rule.
- A list continuation item must fit the body (IEEE needs a leading C or a dot, ANSI and ASTM need a letter glued to the number, NEMA needs letters). It is dropped when a unit word follows (kVA, kV, ft) or when it is the edition of a following NESC. A NEMA item whose letters spell an out-of-scope body (UL, EN) is dropped.
- Line breaks are skipped only between body and number and after "." or "-" inside a number. Dots and hyphens followed by spaces end the designation. A list continuation does not cross a line break: "IEEE C57.12.00,\nC57.12.90" gives one citation. A single letter A or V counts as a unit only when it is uppercase and on the same line as the item.

Options considered:

- Pure 40 character window. Simple, but it binds "Rule 232B2" to the NESC, which the labels do not do.
- A full sentence parser. Too much for a grammar with no catalog.
- The window with an and/or stop (chosen).

A clause number followed by more digits after a dot or hyphen ("Table 232-12345") is rejected, not cut short. "2017 NESC 2018 NESC" gives NESC 2018 and a bare NESC: the first NESC takes the year after it.

## Consequences

A clause written after a misspelled body ("IEE 81, Table 7") still binds to the nearest valid citation before it, because the extractor does not repair misspellings. This shows up as a wrong key, never as a new citation. The written set may label some "X and Rule N" cases the other way; PR 6 measures that once and any change goes to heldout/CHANGES.md.
