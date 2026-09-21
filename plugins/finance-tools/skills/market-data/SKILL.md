---
name: market-data
description: Fetch, normalize, and compare public market data with optional pinned OpenBB and yfinance packages while documenting provenance and limitations.
---

# Market Data

Use this skill for historical prices, company metadata, simple return calculations, and reproducible public-market snapshots.

## Workflow

1. Identify the ticker, exchange, currency, requested interval, and date range.
2. Prefer `scripts/market_snapshot.py` for a small yfinance-based JSON snapshot. The snapshot records adjustment settings, currency and exchange-time-zone availability, null counts, and retrieval provenance.
3. Use OpenBB only when its broader provider coverage or standardized query layer materially helps.
4. Hand price-series analysis to `quant-tools/scripts/return_metrics.py`; it accepts the snapshot JSON directly as well as `date,close` CSV.
5. Include source/provider, retrieval time, adjustments, currency, and missing-data caveats in the result.
6. Distinguish market facts from estimates, analysis, and investment opinion.

## Setup and safety

- Install `requirements.lock.txt` in an isolated environment; plugin installation does not install Python packages.
- Keep provider credentials in a local `.env` or the provider's credential store, never in Git.
- Respect provider terms, rate limits, and permitted data use.
- Treat results as research data, not personalized financial advice.

Use `--output snapshot.json` to save a snapshot without shell-specific redirection. Pass `--no-auto-adjust` when unadjusted OHLC values are required; the selected mode is always recorded in the output.
