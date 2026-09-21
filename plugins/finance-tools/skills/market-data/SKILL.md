---
name: market-data
description: Normalize user-supplied Bloomberg exports or screenshots, apply field-level OpenBB fallbacks, fetch and compare public market data, normalize event calendars, and assess optional finance integrations.
---

# Market Data

Use this skill for historical prices, company data, fundamentals, valuation inputs, earnings research, peer analysis and evaluation of optional financial-research frameworks.

## Workflow

1. Identify the ticker, exchange, currency, requested interval, date range and the user's supplied artifacts.
2. Prefer a user-supplied Bloomberg export or screenshot. For either, read `../../references/bloomberg-inputs.md`; normalize structured rows or visually transcribed screenshot rows with `scripts/normalize_market_input.py`.
3. Preserve task/upload time separately from the provider's price timestamp. If the Bloomberg timestamp is missing or stale, use OpenBB only for the affected fields and merge with `scripts/merge_market_sources.py`; never silently relabel or overwrite the primary observation.
4. When no Bloomberg input is supplied, route a small public price-history request to `scripts/market_snapshot.py`. Use `scripts/openbb_market_snapshot.py --markets APAC --provider fmp` for broad APAC exchange discovery when the pinned OpenBB package and provider are configured, or `--symbols` for a timestamped fallback basket.
5. Use `research-tools` for public filings, investor-relations pages and qualitative evidence that a market-data API does not provide; the user should not need to name that backend.
6. Hand reusable price-series statistics to `quant-tools/scripts/return_metrics.py`; it accepts the snapshot JSON directly as well as `date,close` CSV.
7. Include source/provider, run time, capture window, provider timestamp, adjustments, currency, fallback lineage and missing-data caveats. Distinguish market facts from estimates, analysis and investment opinion.

For catalyst calendars, normalize a supplied event set with `scripts/event_calendar.py`. Keep confirmed and provisional timing distinct, preserve event sources, and never imply that this helper discovers or verifies events. Use a live source or user-supplied calendar first.

## Setup and safety

- Install `requirements.lock.txt` in an isolated environment; plugin installation does not install Python packages.
- Prefer `FINANCE_TOOLS_PYTHON` when configured. Otherwise look for the portable user environment at `~/.codex/venvs/finance-tools/Scripts/python.exe` on Windows or `~/.codex/venvs/finance-tools/bin/python` on macOS/Linux before declaring OpenBB unavailable.
- Keep provider credentials in a local `.env` or the provider's credential store, never in Git.
- Respect provider terms, rate limits, and permitted data use.
- Keep user-supplied Bloomberg screenshots and exports local. Do not commit or redistribute them.
- Treat results as research data, not personalized financial advice.

## Experimental frameworks

- TradingAgents and FinGPT are reference-only evaluation targets, not installed capabilities.
- Do not clone, import, run or provision either framework without an explicitly selected use case, models, data sources, licenses, compute budget, secrets and validation plan.
- Treat TradingAgents as a research orchestration framework, never as an authoritative trading-decision engine.
- Load FinGPT only for a selected financial-NLP workflow; do not make it a default dependency for ordinary finance work.

Use `--output snapshot.json` to save a snapshot without shell-specific redirection. Pass `--no-auto-adjust` when unadjusted OHLC values are required; the selected mode is always recorded in the output.
