---
name: quant-research
description: Design reproducible quantitative-finance analysis with optional gs-quant and evaluate TradingAgents or FinGPT without embedding their repositories.
---

# Quant Research

Use this skill for quantitative research plans, risk and scenario analysis, and framework selection.

## Workflow

1. Define the research hypothesis, universe, horizon, benchmark, and data availability.
2. Specify train, validation, and test windows before evaluating results.
3. Account for survivorship bias, look-ahead bias, data leakage, transaction costs, liquidity, and multiple testing.
4. Use `scripts/return_metrics.py` with a local `date,close` CSV or a `finance-tools` market-snapshot JSON to calculate total return, CAGR, annualized volatility, Sharpe ratio, and maximum drawdown without third-party packages.
5. Use `gs-quant` when its analytics match the task and required data access is available.
6. Report assumptions, sensitivity, failure modes, and reproducibility details.

## Framework boundaries

- `gs-quant==2.1.16` is the only optional package pinned for direct installation here.
- TradingAgents and FinGPT are reference-only. Do not clone, import, run, or provision their model/data stacks as an implicit step.
- If either framework is proposed, first document the exact use case, required models and data, licenses, compute, secrets, and validation plan.
- Never present backtest performance as a guarantee or personalized investment advice.

The return-metrics utility assumes periodic close-to-close observations. It defaults to 252 periods per year; set `--periods-per-year` to match weekly, monthly, or other sampling. Pass `--risk-free-rate` as a decimal annual rate when a nonzero benchmark is needed. Snapshot results retain ticker, provider, retrieval time, interval, currency, adjustment, and missing-close context under `source`.
