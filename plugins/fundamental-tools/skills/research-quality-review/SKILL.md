---
name: research-quality-review
description: Audit public-equity researchability, source independence, management promises, thesis drift, critical numbers, and publication readiness in research_review/v1. Use when checking confidence limits, management delivery, what truly changed in a thesis, or whether a report's important figures are reliable; not for fresh valuation or ordinary prose editing.
---

# Research Quality Review

Challenge the evidence and arithmetic without rewriting the investment conclusion. Read [the research review contract](../../references/research-review.md) before producing or validating `research_review/v1`; use `../../scripts/research_review.py` for deterministic checks.

## Select the needed controls

- Use researchability grading when disclosure, estimate coverage or source access limits confidence.
- Use the management ledger for promise-versus-delivery, capital allocation or governance follow-up.
- Use thesis drift when comparing two research snapshots; distinguish new facts, changed prices/valuation inputs and wording-only edits.
- Use the critical-number audit before publishing a report or memo with material financial figures.

Natural-language requests should trigger the relevant controls automatically. Do not require the user to name every component, and do not run unrelated components merely because they share a plugin.

## Evidence rules

1. Maintain central source and claim registries. Record direct upstream origin and `independence_group`; do not count repeated reporting as independent confirmation.
2. Grade evidence availability separately from company quality or investment merit.
3. Preserve management's original words, dates and target basis. Source the measured outcome separately from the original promise; use a separately sourced rationale for qualitative or partial assessments.
4. Require a prior baseline before making a complete thesis-drift claim. Wording-only edits are substantively unchanged.
5. Audit 100% of declared critical fields with decimal arithmetic. Missing or zero successful verification blocks publication when the audit is required.

## Controls

- Never replace missing evidence with assumed verification.
- Never treat an evidence grade as a buy/sell rating or personalize the conclusion.
- Do not mutate source files, models, broker systems or published research without separate authorization.
- Report unresolved conflicts, limited confidence and the next useful evidence request.
