---
name: market-data
description: Fetch, normalize, and compare public market or company data with pinned OpenBB and yfinance integrations, or assess optional financial-research frameworks without embedding them.
---

# Market Data

Use this skill for historical prices, company data, fundamentals, valuation inputs, earnings research, peer analysis and evaluation of optional financial-research frameworks.

## Workflow

1. Identify the ticker, exchange, currency, requested interval, and date range.
2. Route a small public price-history request to `scripts/market_snapshot.py`. The snapshot records adjustment settings, currency and exchange-time-zone availability, null counts, and retrieval provenance.
3. Route broader provider coverage, fundamentals or standardized queries to OpenBB only when its pinned optional package is installed and materially helps.
4. Use `research-tools` for public filings, investor-relations pages and qualitative evidence that a market-data API does not provide; the user should not need to name that backend.
5. Hand reusable price-series statistics to `quant-tools/scripts/return_metrics.py`; it accepts the snapshot JSON directly as well as `date,close` CSV.
6. Include source/provider, retrieval time, adjustments, currency, and missing-data caveats in the result. Distinguish market facts from estimates, analysis and investment opinion.

## Setup and safety

- Install `requirements.lock.txt` in an isolated environment; plugin installation does not install Python packages.
- Keep provider credentials in a local `.env` or the provider's credential store, never in Git.
- Respect provider terms, rate limits, and permitted data use.
- Treat results as research data, not personalized financial advice.

## Experimental frameworks

- TradingAgents and FinGPT are reference-only evaluation targets, not installed capabilities.
- Do not clone, import, run or provision either framework without an explicitly selected use case, models, data sources, licenses, compute budget, secrets and validation plan.
- Treat TradingAgents as a research orchestration framework, never as an authoritative trading-decision engine.
- Load FinGPT only for a selected financial-NLP workflow; do not make it a default dependency for ordinary finance work.

Use `--output snapshot.json` to save a snapshot without shell-specific redirection. Pass `--no-auto-adjust` when unadjusted OHLC values are required; the selected mode is always recorded in the output.
