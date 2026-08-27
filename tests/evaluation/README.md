# Ground-Truth Evaluation

`ground_truth.json` is a deliberately small, manually established baseline for
seven local images. Values were transcribed only when legible in the source
image. The blurred sample has no asserted fields, and omitted fields in every
other record are unknown rather than negative labels.

Run the evaluator from the repository root:

```sh
.venv/bin/python -m tests.evaluation.evaluate
```

Comparison rules are intentionally conservative:

- Exact matching preserves the original extracted string.
- Normalized matching ignores case, repeated whitespace, and punctuation
  boundaries.
- MRP and unit-sale-price values additionally compare as numbers, so `50` and
  `50.00` match.
- No semantic rewriting, OCR correction, or fuzzy matching is performed.
- Uncertain extraction status is reported even when the value matches.
- Unknown fields are not scored and cannot produce false positives.
- A record may use `not_expected` for fields known to be absent; those are
  reported as explicit false positives if extraction returns them.

The selected images cover clear, darker, blurred, dense, small-text, and
rotated conditions. This file is an evaluation artifact only; it does not
alter the production pipeline.
