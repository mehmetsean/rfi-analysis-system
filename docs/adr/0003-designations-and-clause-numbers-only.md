# 3. Designations and clause numbers only, never standard text

Status: Accepted

## Context

Standards are copyrighted by their owners. ASTM's copyright page bars copying its text. A designation such as "IEEE C57.12.00-2015" and a clause number such as "Rule 232B1" are identifiers, not the text of a standard.

## Decision

Code, data, labels, templates and output hold only designations and clause numbers. No titles, no requirements, no quotes from a standard. Templates never state what a standard requires. The names IEEE, NESC, IEC, ANSI, ASTM and NEMA identify their documents only, and the project has no affiliation with them.

Options considered:

- A catalog with titles and summaries. Helpful to readers, but it copies owned text.
- Lookup of each designation against a list. Misses new standards and needs upkeep.
- Identifiers only, read by grammar (chosen). Finds standards the author never saw.

## Consequences

The tool cannot say whether a standard applies or what it requires. Readers check each citation against the official standard.
