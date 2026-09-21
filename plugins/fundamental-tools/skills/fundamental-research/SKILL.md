---
name: fundamental-research
description: Build auditable public-company fundamental packs, normalize reported financials, calculate transparent ratios and DCF scenarios, and route optional APAC filing adapters. Use for listed-company fundamentals, coverage work, model updates, valuation, peer preparation, or what-changed analysis; not for private-company diligence or personalized financial advice.
---

# Fundamental Research

Build the evidence and calculation layer before drafting an investment view. This skill owns source normalization, provenance, calculation transparency and `fundamental_pack/v1`; it does not silently turn a data gap into an estimate.

## Workflow

1. Identify the issuer, primary listing, exchange, reporting currency, fiscal periods and requested investor use case.
2. Read [provider selection](../../references/provider-selection.md) and use the highest-ranked available source. Prefer user-supplied Bloomberg/model exports and official company, exchange or regulator filings. Use aggregators only as labeled fallbacks.
3. Run `scripts/provider_adapters.py capabilities` when optional integration availability is unclear. Never claim a package, credential, entitlement or live connection that the capability report does not support.
4. Preserve raw provider output in an adapter envelope. Map it into the schema in [fundamental pack contract](../../references/fundamental-pack.md); retain source IDs, retrieved-at time, report date, currency, scale, basis and conflicts.
5. Run `scripts/fundamental_pack.py` to calculate comparable operating metrics, market multiples and DCF scenarios. Treat its output as deterministic math, not analyst judgment.
6. Explain revenue/profit/cash conversion, balance-sheet capacity, estimate or guidance changes, valuation, catalysts, risks, what is priced in, and explicit prove/kill conditions. Distinguish facts, management claims, consensus, derived calculations and assumptions.
7. State readiness (`ready`, `limited` or `blocked`), unresolved conflicts, missing sources, data cut-off and the next useful research step.

## Integration boundary

- FinanceToolkit and FinanceDatabase are optional local engines. They do not outrank official filings or a fresher user-supplied source.
- J-Quants, OpenDART and TWSE are preferred country routes for Japan, Korea and Taiwan when available and permitted.
- EdgarTools supports US filings and APAC ADRs. AKShare is a labeled China/HK fallback whose upstream page/API stability must be monitored.
- Anthropic Financial Services is a workflow reference only; do not import its Claude-specific constraints, fixed report lengths or recommendation language.
- When the installed Public Equity Investing plugin owns the requested hero deliverable (for example initiating coverage, comps, a DCF workbook, model update or thesis tracker), use this skill as its evidence/calculation layer and preserve that owning workflow's output standards.

## Controls

- Read-only research only. Do not mutate brokerage accounts, orders, positions, alerts or watchlists.
- Keep credentials in environment variables; never print or persist secret values.
- Respect upstream licenses, terms, rate limits and entitlements. Plugin installation does not install Python packages or grant data rights.
- Do not mix annual, quarterly, TTM, reported, adjusted, consensus or analyst estimates without explicit labels.
- Do not present a target price or recommendation when current market data, share count, net debt, financial history or valuation assumptions are materially unsupported.
- Treat generated research as educational analysis, not personalized financial advice.

## Commands

```shell
python scripts/provider_adapters.py capabilities
python scripts/provider_adapters.py twse --code 2330 --statement income --output twse.json
python scripts/provider_adapters.py jquants --code 7203 --output jquants.json
python scripts/provider_adapters.py opendart --corp 005930 --year 2025 --output dart.json
python scripts/fundamental_pack.py input.json --output fundamental-pack.json --strict
```

Use source-specific optional environments from the plugin requirements files. A missing optional dependency should produce a clear setup requirement or reduced-scope workflow, not an automatic installation attempt.
