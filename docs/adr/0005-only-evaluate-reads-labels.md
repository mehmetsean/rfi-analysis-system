# 5. Only the evaluate module reads labels

Status: Accepted

## Context

Measured rates mean nothing if a method can see the answers. Labels live in files next to the synthetic and written RFIs.

## Decision

Only the evaluate module reads label files. Extraction code (and later classification and grouping) imports neither synth nor evaluate. Labels come from the generator's record of where it inserted each item, never from running the extractor. A planned test will check that blanking the label files changes no prediction.

Options considered:

- Labels passed into every method for convenience. Easy, but it allows leaks.
- A convention only. Cheap, but nothing stops a slip.
- One reader module plus an import check and a blanking test (chosen).

## Consequences

Methods take plain text and return predictions. Scoring code is the one place that joins predictions with labels.
