# 4. One span convention for citations

Status: Accepted

## Context

Scoring citations needs one clear rule for where a span starts and ends. Clauses and editions can sit before or after the designation.

## Decision

start and end cover the designation only, from the first character of the body token (of the number for a list item, of the edition when it comes first as in "2017 NESC") to the last character of the number, part, year or suffix. A clause has its own clause_start and clause_end and is scored in the full key, never in the strict span. An inferred bare NESC rule or table has no designation text, so its clause offsets are its span. Offsets count Unicode code points. Text cleanup is a one-to-one character map, so offsets in cleaned text are offsets in the original.

Options considered:

- Span includes the clause. Simple to read, but the same standard gets spans of different length.
- Span is the body token only. Easy to find, but it hides errors in the number and year.
- Designation only, clause apart (chosen).

## Consequences

Strict span scoring and key scoring are separate. Example: in "2017 NESC Rule 232B1" the span is "2017 NESC", the clause is "Rule 232B1", the full key is "NESC 2017 Rule 232B1" and the base key is "NESC Rule 232B1". The planned demo will convert offsets to UTF-16 units at the Pyodide boundary.
