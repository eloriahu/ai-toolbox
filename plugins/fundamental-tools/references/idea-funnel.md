# `idea_funnel/v1`

This contract records how an observed move, event or structural theme becomes a ranked research funnel. It preserves failed links and rejected names so a polished narrative cannot hide the narrowing process.

## Top-level contract

- `schema`: exactly `idea_funnel/v1`
- `schemaVersion`: `1`
- `as_of`: ISO 8601 timestamp with timezone offset
- `question`: the research question, not a recommendation request
- `scope`: markets, sectors, liquidity constraints and explicit exclusions
- `sources`: central source registry
- `claims`: central claim registry
- `causal_chain`: traceable links from observation to earnings mechanism
- `causal_gate`: blocking required links and the ranking decision
- `bottlenecks`: scored physical, regulatory, qualification or capacity constraints
- `screen_profiles`: explicit sector or income-durability rules
- `candidates`: advanced, watched and rejected names
- `ranking`: only candidates that pass the evidence and required-screen gates
- `quality`: readiness, gaps, warnings and performed checks

Each source needs `id`, direct `origin` and `independence_group`. Use the same independence group for an issuer release and articles that merely repeat it. Each claim needs `id`, `statement` and valid `source_ids`; an invalid claim cannot support another object. Analysis objects can point to central claims with `claim_ids` or directly to sources with `source_ids`.

## Causal chain and bottlenecks

Every causal link has `from`, `to`, `mechanism`, valid evidence lineage, `required` (default `true`) and one status: `supported`, `disputed`, `unsupported` or `unknown`. Every required link must be supported and lineage-valid before any candidate can rank. Do not remove a disputed or unsupported link; it may explain why an attractive theme does not reach a listed company's earnings.

Bottlenecks use six evidence-backed scores from 0 to 5:

- supplier concentration
- capacity tightness
- expansion lead time
- qualification friction
- substitution difficulty
- demand-capacity gap

Weights may be supplied explicitly; omitted weights default equally. The builder calculates a 0–100 score only when all six dimensions are present. A bottleneck score ranks constraints; it does not prove that a security is attractive.

## Candidate evidence and ranking

An advanced or watched candidate needs a listing identity (`name`, `primary_symbol`, `exchange`), `supply_chain_position`, a lineage-valid `exposure.description` (plus quantified revenue/profit exposure when supportable), a declared `screen_profile_id`, and evidence in six lanes: exposure, fundamentals, expectations, valuation, catalysts and falsifiers. It also needs 0–5 scores for exposure purity, bottleneck leverage, fundamental quality, expectations gap, valuation asymmetry, catalyst credibility and falsifier resilience.

The builder applies supplied weights or an equal-weight default and produces a 0–100 ranking score only when every score has valid lineage. Bottleneck scores follow the same rule. It never derives a buy/sell label, position size or order instruction. `advance`, `watch` and `reject` are research dispositions. Every rejected company retains all supplied `rejection_reasons`.

## Sector-aware and income screens

There are no universal ROE, margin, leverage or payout cutoffs. Supply a `screen_profile` with its sector, purpose and rules. Every rule identifies a metric, operator and threshold or range. Candidate inputs preserve four states: `pass`, `fail`, `insufficient` and `not_applicable`.

An income-durability profile may use metrics such as distribution coverage, free cash flow after distributions, leverage, payout volatility, payout-history length and refinancing headroom. Banks, insurers, REITs, commodity producers and operating companies should use different profiles. Record the source and rationale for each threshold in the profile.

The supported numeric operators are `gt`, `gte`, `lt`, `lte`, `eq` and `between`. A missing required metric produces `insufficient`; it is never silently treated as a pass or zero. Every advanced or watched candidate must select a found profile; the profile must contain at least one applicable required rule and resolve to `pass`. No-profile, empty and wholly not-applicable profiles do not satisfy the ranking gate.

The CLI parses JSON decimal literals directly into `Decimal` and emits exact decimal strings. Direct Python callers should supply `Decimal`, integers or numeric strings; binary `float` inputs are rejected rather than rounded silently.

## Quality states

- `ready`: foundational fields exist and every advanced/watched candidate is rankable.
- `limited`: the funnel is usable but at least one evidence, score, rule or ranking gap remains.
- `blocked`: the timestamp, question, scope, source registry, claim registry, causal chain or candidate universe is absent.

Run:

```shell
python scripts/idea_funnel.py input.json --output idea-funnel.json --strict
python scripts/idea_funnel.py idea-funnel.json --validate-only --strict
```

Validation-only mode recomputes the causal gate, screens, evidence coverage, scores and ranking. It does not trust stored derived summaries. With `--strict`, structurally valid but `limited` or `blocked` packs still exit nonzero.
