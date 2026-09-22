# `research_review/v1`

This contract keeps research confidence, management delivery, thesis changes and publication checks separate from the investment conclusion.

## Top-level contract

- `schema`: exactly `research_review/v1`
- `schemaVersion`: `1`
- `as_of`: ISO 8601 timestamp with timezone offset
- `entity`: company identity
- `sources`: central source registry with direct `origin` and `independence_group`
- `claims`: central sourced claim registry
- `researchability`: evidence coverage and maximum supported confidence
- `management_ledger`: promise-versus-delivery records
- `thesis_drift`: fact, price and wording comparison
- `number_audit`: decimal-safe critical-number verification
- `publication_gate`: `pass`, `blocked` or `not_run`
- `quality`: contract readiness and unresolved issues

Use the same `independence_group` for copies or summaries derived from one upstream source. The number audit reports both source IDs and independent-source counts; a syndicated article does not become a second confirmation.

## Researchability

Describe the evidence lanes needed for the actual assignment, for example primary filings, financial history, management disclosures, market data, consensus and industry data. Each lane is `complete`, `partial`, `missing` or `not_applicable`, with an explicit weight and sources where evidence exists.

The builder calculates evidence coverage and assigns:

- `A` / high maximum confidence: at least 80% weighted coverage and no required lane missing
- `B` / medium: at least 50% coverage with traceable sources
- `C` / low: weaker support

These are evidence grades, not investment ratings. They do not compare the company with sector thresholds.

## Management ledger

Each record retains the original promise, statement date, deadline and promise source. A measured outcome needs its own `measurement.source_ids`; it cannot inherit the original promise's source. Exact numeric promises can use `gt`, `gte`, `lt`, `lte`, `eq` or `between`; the script evaluates them with decimal arithmetic. A target already achieved can be `delivered` early, but a below-target observation remains `pending` until its deadline. Qualitative, partial or withdrawn commitments require an explicit analyst assessment with separate sources and rationale. Status is one of `delivered`, `partial`, `missed`, `pending`, `withdrawn` or `unclear`.

Do not convert a vague aspiration into a quantified promise. Keep management's claim and the analyst's assessment distinct.

## Thesis drift

Provide `prior` and `current` maps for `facts`, `prices` and `wording`. The output records every changed path and exposes:

- `primary_class`: `fact`, `price`, `wording` or `no_change`
- `substantive_state`: `facts_changed`, `valuation_changed` or `unchanged`
- `comparison_status`: `complete` or `limited_no_baseline`
- `effect_on_conclusion`: sourced direction (`strengthened`, `weakened`, `falsified`, `unchanged` or `unclear`) and rationale for substantive changes

A wording-only rewrite remains substantively unchanged. A price or valuation-input change is not mislabeled as a changed operating fact. A new or changed fact must carry source IDs. With no prior baseline, the review is limited rather than claiming that nothing changed.

## Critical-number audit

Set `number_audit.required` to `true`, enumerate every `critical_field`, and provide a uniquely identified row for each field. A row contains report and source values plus currency, unit, positive scale, period and basis on both sides; missing or invalid metadata makes the row unverifiable. Optional absolute and relative tolerances must be explicit and non-negative.

The script uses `Decimal`, serializes exact results as decimal strings and blocks publication when:

- a declared critical field has no row;
- a critical row fails or is unverifiable;
- required source lineage or source-independence is missing;
- no field is verified; or
- the critical-field scope was not declared.

Set `minimum_independent_sources` only when the claim genuinely requires corroboration. It must be a positive integer. One primary filing can be sufficient for a reported number; multiple articles derived from it still count as one independent group.

The CLI parses JSON decimal literals directly into `Decimal` and emits exact decimal strings. Direct Python callers should supply `Decimal`, integers or numeric strings; binary `float` inputs are rejected rather than rounded silently.

Run:

```shell
python scripts/research_review.py input.json --output research-review.json --strict
python scripts/research_review.py research-review.json --validate-only --strict
```

Validation-only mode recomputes evidence coverage, management delivery, thesis-change summaries, every number-audit row and the publication gate. It does not trust stored pass counts or readiness fields. With `--strict`, both quality `ready` and publication gate `pass` are required; `not_run` is not a strict pass.
