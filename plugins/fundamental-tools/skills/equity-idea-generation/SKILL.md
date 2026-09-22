---
name: equity-idea-generation
description: Trace a public-equity theme, bottleneck, supply-chain change, or observed company or sector move into evidenced listed-company candidates and an idea_funnel/v1 ranking. Use for second-order implications, who benefits or loses, theme-to-names, bottleneck scans, sector funnels, and idea generation after a price move; not for raw tape explanation without idea implications or personalized trade sizing.
---

# Equity Idea Generation

Turn a market observation into a falsifiable research funnel. Select only the lanes the question needs; a simple move explanation does not justify running every available workflow.

## Route the request

- For a structural theme, start with the causal chain and bottleneck map.
- For “this stock is up—what follows?”, first establish the observed move and strongest supported catalyst, then trace earnings, peer, supplier, customer and substitution implications.
- For a broad sector request, build an inclusive universe before applying exposure, liquidity and user-supplied sector screens.
- For a named company without an idea-generation question, leave company fundamentals to `fundamental-research`.
- When the user asks whether evidence, management delivery, thesis changes or report numbers are reliable, use `research-quality-review`.

Read [the idea funnel contract](../../references/idea-funnel.md) before building or validating the pack. Use `../../scripts/idea_funnel.py` for screen evaluation, bottleneck scores, evidence gates and ranking.

## Research discipline

1. Verify the observation or structural trend before explaining it.
2. Test each causal link: observation → incremental demand or risk → scarce capacity/constraint → earnings exposure → listed candidate.
3. Search both beneficiaries and losers, including substitutes and capacity additions that could dissolve the bottleneck.
4. Record the initial universe and retain every exclusion reason. Do not backfill a universe around a preferred answer.
5. Separate business exposure, earnings sensitivity, market expectations, valuation, dated catalysts and falsifiers.
6. Use explicit sector/profile rules. Preserve `not_applicable` and `insufficient`; never apply one quality or payout threshold to every industry.
7. Rank only traceable, complete candidates. Treat the result as a research priority list, not a trade instruction.

## Parallel research

When breadth or independence genuinely helps and parallel agents are available, divide work by function: business/KPIs, filings/accounting, industry/supply chain, and expectations/valuation/catalysts. Use a separate bear-case or verifier pass for consequential outputs. Reconcile conflicts against sources; do not average agent scores or use investor personas as evidence.

## Controls

- Keep a central claim/source registry and group sources by their true upstream origin.
- Do not infer position sizes, orders or personalized suitability.
- Do not silently install packages, access accounts or publish research.
- Label unsupported links and unrankable names instead of completing them with prose.
