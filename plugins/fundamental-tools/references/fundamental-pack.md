# `fundamental_pack/v1`

The pack is the loose-coupling boundary between reusable data/calculation tools and an investor-facing workflow such as APAC Equity Desk or Public Equity Investing.

## Required top-level fields

- `schema`: exactly `fundamental_pack/v1`
- `schemaVersion`: `1`
- `as_of`: ISO 8601 timestamp with timezone offset
- `entity`: `name`, `primary_symbol`, `exchange`, `country`, `reporting_currency`; optional stable identifiers and provider symbols
- `sources`: nonempty source register with unique IDs
- `financials.periods`: comparable reported or estimated periods
- `metrics`: deterministic calculations generated from the period values
- `valuation`: market inputs, multiples and optional DCF scenarios
- `expectations`: consensus/guidance inputs, kept separate from reported data
- `thesis`: claims, debates, catalysts, risks and falsifiers with source IDs
- `quality`: readiness, missing fields, warnings, conflicts and performed checks

## Financial period

Each period contains:

- `period_end`, `period_type` (`FY`, `Q`, `H`, `TTM`), optional fiscal year/quarter
- `currency`, `unit_scale`, `basis`, `report_status`, `source_ids`
- `values`, using canonical snake-case keys where available:
  `revenue`, `cost_of_goods_sold`, `gross_profit`, `ebitda`, `operating_income`, `interest_expense`, `tax_expense`, `net_income`, `operating_cash_flow`, `capital_expenditure`, `free_cash_flow`, `cash`, `total_debt`, `total_assets`, `total_equity`, `diluted_shares`

Keep provider-native labels in `reported_labels` or the preserved raw adapter envelope. Do not coerce a value whose scale, currency or basis is unknown.

## Evidence labels

Use one of: `fact_source_reported`, `fact_provider_standardized`, `issuer_management_claim`, `estimate_consensus`, `derived_calculation`, `assumption_user_provided`, `assumption_inferred`, `contradicted_source`, `stale_source`, `missing_required_source`, `unknown`.

## DCF assumptions

`valuation.dcf_assumptions` may include `base_revenue`, `forecast_years`, `revenue_growth`, `ebit_margin`, `tax_rate`, `da_pct_revenue`, `capex_pct_revenue`, `nwc_pct_revenue`, `wacc`, `terminal_growth`, `net_debt` and `diluted_shares`. Rates are decimals. A scalar or a list may be supplied for the forecast drivers. `valuation.scenarios` contains named overrides.

The calculator refuses `wacc <= terminal_growth`, non-positive shares or an empty forecast. It returns enterprise value, equity value, value per share, explicit-period present value and terminal-value share so the user can see when the result is overly terminal-dependent.

## Readiness

- `ready`: primary evidence is traceable, periods are usable and no material warning remains.
- `limited`: useful analysis is possible but at least one source, comparison, market input or validation issue remains.
- `blocked`: no traceable source, no usable financial period, invalid as-of time or another foundational input is absent.

Strict CLI mode exits nonzero for a blocked pack. It does not require valuation when the requested job is statement normalization only.
