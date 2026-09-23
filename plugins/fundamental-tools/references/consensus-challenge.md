# `consensus_challenge/v1`

This pack measures agreement on a specific sell-side thesis and makes its premises inspectable. It is not a sentiment score, a claim of analyst misconduct or a trading recommendation.

Input to `scripts/consensus_challenge.py`:

- Offset-dated `as_of`, issuer/listing `entity`, optional `window_days` (default 90) and `minimum_supporting_groups` (minimum 3).
- `eligible_houses`: explicit large-house coverage universe, each with `id` and optional common-parent `group`. `universe_basis` records why those houses belong. Without both, the gate is `unverified_universe`, never “mainstream.” Related desks in one group count once.
- `sources`: unique `id`, direct `origin`, `independence_group`, offset `published_at`, and ideally `source_type`, access rights and URL. Each counted report source needs the corresponding `house_id`; one multi-house media summary cannot substitute for separate house reports. Do not store proprietary full-text notes in the pack or repository.
- `theses`: unique `id`, specific `statement`, `direction` (`bullish`/`bearish`), `horizon`, and nonempty `premises` with unique IDs, statement, supporting `source_ids` and an explicit falsifier when known. A shared rating is not a shared thesis.
- `views`: `house_id`, `thesis_id`, matching `horizon`, `stance` (`supports`/`opposes`/`neutral`), offset `published_at`, report `source_id`, `premise_ids`, underlying `basis_source_ids`, `reviewed_full_text` and `addressed_counterevidence_ids`. One latest fresh view per house group and thesis is counted. The report source must exist and predate or match the view date.
- `counterevidence`: unique `id`, linked `premise_id`, statement, `source_ids`, and status `candidate`, `primary_checked` or `refuted`. “Primary checked” is an analyst assertion requiring independent source inspection; the script does not verify document semantics.

The mainstream gate is `established` only if the declared eligible universe has a documented basis, at least three distinct fresh house groups support the *same* thesis, and those groups are a strict majority of all eligible house groups. Otherwise it is `not_established` or `unverified_universe`. Stale reports are excluded and counted. `shared_basis_groups` shows common underlying information sources, not proof of herding or error.

The challenge queue highlights unsupported premises, missing falsifiers, sourced counterevidence and whether it was addressed in the supplied reports. `unaddressed_in_reviewed_sample_ids` is populated only when every supporting report was reviewed in full and none addresses that item. It never proves that nobody in the market has noticed it. Every row has `novelty_status: not_established`; the analyst must search disconfirming published work, verify primary data and decide whether a flaw is material, already priced, or not a flaw at all.

Output contains `schema`, `schemaVersion`, concise source and claim metadata, `analyses`, `challenge_queue` and `quality`. Unknown raw-report fields are discarded by the producer; claim text is length-limited, but the analyst must still paraphrase rather than paste licensed text. A consuming desk should preserve the pack's fields and source IDs while owning interpretation, current valuation context, verification and writing.
