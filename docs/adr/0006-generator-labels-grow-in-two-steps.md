# 6. Generated rfis.csv grows in two steps

Status: Accepted

## Context

The generator is built in two PRs. PR 4a writes the RFIs with citation, negative and noise labels. PR 4b adds the issue type and group labels. The reader for labels/rfis.csv required all five columns (rfi_id, issue_type, group_id, template_id, family), so a file from 4a would be rejected.

## Decision

The reader requires rfi_id, template_id and family. The issue_type and group_id columns are optional. When a column is missing, the value is empty. When a column is present, its values are checked as before, so the written set and the files from 4b get the full check. PR 4a writes labels/rfis.csv with only rfi_id, template_id and family. PR 4b adds the two columns and its own tests.

Options considered:

- Write issue_type and group_id now, taken from the template. This would ship labels that 4b is meant to test and own.
- Write placeholder values. The reader would still reject an empty issue type, and a placeholder looks like a real label.
- Make the two columns optional in the reader (chosen).

## Consequences

A file without the two columns cannot be told apart from a file that lost them. The 4b tests will require both columns in generated output, so a loss shows up there.
