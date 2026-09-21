"""Build and validate the dependency-free ``fundamental_pack/v1`` contract."""

from __future__ import annotations

import argparse
import copy
import json
import math
from datetime import datetime
from pathlib import Path
from typing import Any


SCHEMA = "fundamental_pack/v1"
CANONICAL_VALUES = {
    "revenue",
    "cost_of_goods_sold",
    "gross_profit",
    "ebitda",
    "operating_income",
    "interest_expense",
    "tax_expense",
    "net_income",
    "operating_cash_flow",
    "capital_expenditure",
    "free_cash_flow",
    "cash",
    "total_debt",
    "total_assets",
    "total_equity",
    "diluted_shares",
}


def number(value: Any) -> float | None:
    """Return a finite float from common provider number formats."""
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        result = float(value)
    else:
        text = str(value).strip()
        if not text or text.lower() in {"n/a", "na", "nan", "none", "null", "-"}:
            return None
        negative = text.startswith("(") and text.endswith(")")
        percent = text.endswith("%")
        text = text.strip("()").replace(",", "").replace("%", "")
        try:
            result = float(text)
        except ValueError:
            return None
        if negative:
            result = -result
        if percent:
            result /= 100
    return result if math.isfinite(result) else None


def divide(numerator: Any, denominator: Any) -> float | None:
    num = number(numerator)
    den = number(denominator)
    if num is None or den in {None, 0.0}:
        return None
    return num / den


def _rounded(value: float | None) -> float | None:
    return None if value is None else round(value, 8)


def _period_sort_key(period: dict[str, Any]) -> tuple[str, str]:
    return (str(period.get("period_end") or ""), str(period.get("period_type") or ""))


def calculate_period_metrics(periods: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Calculate transparent metrics without mutating reported values."""
    output: list[dict[str, Any]] = []
    prior_by_type: dict[str, dict[str, Any]] = {}
    for period in sorted(periods, key=_period_sort_key):
        values = period.get("values") if isinstance(period.get("values"), dict) else {}
        clean = {key: number(values.get(key)) for key in CANONICAL_VALUES}
        revenue = clean["revenue"]
        gross_profit = clean["gross_profit"]
        if gross_profit is None and revenue is not None and clean["cost_of_goods_sold"] is not None:
            gross_profit = revenue - clean["cost_of_goods_sold"]
        free_cash_flow = clean["free_cash_flow"]
        if free_cash_flow is None and clean["operating_cash_flow"] is not None and clean["capital_expenditure"] is not None:
            free_cash_flow = clean["operating_cash_flow"] - abs(clean["capital_expenditure"])
        net_debt = None
        if clean["total_debt"] is not None or clean["cash"] is not None:
            net_debt = (clean["total_debt"] or 0.0) - (clean["cash"] or 0.0)

        period_type = str(period.get("period_type") or "unknown")
        prior_values = prior_by_type.get(period_type, {}).get("values", {})
        prior_revenue = number(prior_values.get("revenue"))
        prior_equity = number(prior_values.get("total_equity"))
        prior_assets = number(prior_values.get("total_assets"))
        average_equity = None
        average_assets = None
        if clean["total_equity"] is not None:
            average_equity = (
                clean["total_equity"]
                if prior_equity is None
                else (clean["total_equity"] + prior_equity) / 2
            )
        if clean["total_assets"] is not None:
            average_assets = (
                clean["total_assets"]
                if prior_assets is None
                else (clean["total_assets"] + prior_assets) / 2
            )

        effective_tax_rate = divide(clean["tax_expense"], clean["operating_income"])
        tax_rate = effective_tax_rate if effective_tax_rate is not None else 0.0
        invested_capital = None
        if clean["total_debt"] is not None and clean["total_equity"] is not None:
            invested_capital = clean["total_debt"] + clean["total_equity"] - (clean["cash"] or 0.0)
        nopat = None
        if clean["operating_income"] is not None:
            nopat = clean["operating_income"] * (1 - max(0.0, min(tax_rate, 1.0)))

        metrics = {
            "revenue_growth": divide(
                None if prior_revenue is None or revenue is None else revenue - prior_revenue,
                prior_revenue,
            ),
            "gross_margin": divide(gross_profit, revenue),
            "ebitda_margin": divide(clean["ebitda"], revenue),
            "operating_margin": divide(clean["operating_income"], revenue),
            "net_margin": divide(clean["net_income"], revenue),
            "free_cash_flow": free_cash_flow,
            "free_cash_flow_margin": divide(free_cash_flow, revenue),
            "cash_conversion": divide(clean["operating_cash_flow"], clean["net_income"]),
            "capex_intensity": divide(
                None if clean["capital_expenditure"] is None else abs(clean["capital_expenditure"]),
                revenue,
            ),
            "return_on_equity": divide(clean["net_income"], average_equity),
            "return_on_assets": divide(clean["net_income"], average_assets),
            "return_on_invested_capital": divide(nopat, invested_capital),
            "net_debt": net_debt,
            "net_debt_to_ebitda": divide(net_debt, clean["ebitda"]),
            "interest_coverage": divide(
                clean["operating_income"],
                None if clean["interest_expense"] is None else abs(clean["interest_expense"]),
            ),
        }
        output.append(
            {
                "period_end": period.get("period_end"),
                "period_type": period.get("period_type"),
                "metrics": {
                    key: _rounded(value)
                    for key, value in metrics.items()
                    if value is not None
                },
                "evidence_label": "derived_calculation",
                "source_ids": list(period.get("source_ids") or []),
            }
        )
        prior_by_type[period_type] = {"values": clean}
    return output


def calculate_market_valuation(
    latest_period: dict[str, Any] | None,
    market_data: dict[str, Any],
) -> dict[str, Any]:
    values = latest_period.get("values", {}) if latest_period else {}
    price = number(market_data.get("price"))
    shares = number(market_data.get("diluted_shares")) or number(values.get("diluted_shares"))
    market_cap = number(market_data.get("market_cap"))
    if market_cap is None and price is not None and shares is not None:
        market_cap = price * shares
    net_debt = number(market_data.get("net_debt"))
    if net_debt is None and latest_period:
        debt = number(values.get("total_debt"))
        cash = number(values.get("cash"))
        if debt is not None or cash is not None:
            net_debt = (debt or 0.0) - (cash or 0.0)
    enterprise_value = number(market_data.get("enterprise_value"))
    if enterprise_value is None and market_cap is not None and net_debt is not None:
        enterprise_value = market_cap + net_debt
    fcf = number(values.get("free_cash_flow"))
    if fcf is None and number(values.get("operating_cash_flow")) is not None and number(values.get("capital_expenditure")) is not None:
        fcf = number(values.get("operating_cash_flow")) - abs(number(values.get("capital_expenditure")))

    multiples = {
        "price_to_earnings": divide(market_cap, values.get("net_income")),
        "price_to_book": divide(market_cap, values.get("total_equity")),
        "enterprise_value_to_sales": divide(enterprise_value, values.get("revenue")),
        "enterprise_value_to_ebitda": divide(enterprise_value, values.get("ebitda")),
        "free_cash_flow_yield": divide(fcf, market_cap),
    }
    return {
        "market_data": {
            **copy.deepcopy(market_data),
            "price": price,
            "diluted_shares": shares,
            "market_cap": market_cap,
            "net_debt": net_debt,
            "enterprise_value": enterprise_value,
        },
        "multiples": {
            key: _rounded(value)
            for key, value in multiples.items()
            if value is not None
        },
    }


def _driver_series(value: Any, years: int, name: str) -> list[float]:
    raw = value if isinstance(value, list) else [value] * years
    if len(raw) != years:
        raise ValueError(f"{name} must contain exactly {years} values")
    values = [number(item) for item in raw]
    if any(item is None for item in values):
        raise ValueError(f"{name} contains a non-numeric value")
    return [float(item) for item in values if item is not None]


def calculate_dcf(assumptions: dict[str, Any]) -> dict[str, Any]:
    years = int(number(assumptions.get("forecast_years")) or 0)
    if years <= 0 or years > 20:
        raise ValueError("forecast_years must be between 1 and 20")
    base_revenue = number(assumptions.get("base_revenue"))
    shares = number(assumptions.get("diluted_shares"))
    wacc = number(assumptions.get("wacc"))
    terminal_growth = number(assumptions.get("terminal_growth"))
    if base_revenue is None or base_revenue <= 0:
        raise ValueError("base_revenue must be positive")
    if shares is None or shares <= 0:
        raise ValueError("diluted_shares must be positive")
    if wacc is None or terminal_growth is None or wacc <= terminal_growth:
        raise ValueError("wacc must be greater than terminal_growth")

    growth = _driver_series(assumptions.get("revenue_growth"), years, "revenue_growth")
    margins = _driver_series(assumptions.get("ebit_margin"), years, "ebit_margin")
    taxes = _driver_series(assumptions.get("tax_rate"), years, "tax_rate")
    da_rates = _driver_series(assumptions.get("da_pct_revenue", 0.0), years, "da_pct_revenue")
    capex_rates = _driver_series(assumptions.get("capex_pct_revenue", 0.0), years, "capex_pct_revenue")
    nwc_rates = _driver_series(assumptions.get("nwc_pct_revenue", 0.0), years, "nwc_pct_revenue")

    forecast: list[dict[str, Any]] = []
    revenue = base_revenue
    prior_nwc = base_revenue * nwc_rates[0]
    pv_explicit = 0.0
    for year in range(1, years + 1):
        revenue *= 1 + growth[year - 1]
        ebit = revenue * margins[year - 1]
        nopat = ebit * (1 - taxes[year - 1])
        depreciation = revenue * da_rates[year - 1]
        capex = revenue * capex_rates[year - 1]
        nwc = revenue * nwc_rates[year - 1]
        change_nwc = nwc - prior_nwc
        unlevered_fcf = nopat + depreciation - capex - change_nwc
        discount_factor = (1 + wacc) ** year
        present_value = unlevered_fcf / discount_factor
        pv_explicit += present_value
        forecast.append(
            {
                "year": year,
                "revenue": _rounded(revenue),
                "ebit": _rounded(ebit),
                "unlevered_free_cash_flow": _rounded(unlevered_fcf),
                "present_value": _rounded(present_value),
            }
        )
        prior_nwc = nwc

    terminal_value = forecast[-1]["unlevered_free_cash_flow"] * (1 + terminal_growth) / (wacc - terminal_growth)
    pv_terminal = terminal_value / ((1 + wacc) ** years)
    enterprise_value = pv_explicit + pv_terminal
    net_debt = number(assumptions.get("net_debt")) or 0.0
    equity_value = enterprise_value - net_debt
    value_per_share = equity_value / shares
    return {
        "assumptions": copy.deepcopy(assumptions),
        "forecast": forecast,
        "present_value_explicit": _rounded(pv_explicit),
        "present_value_terminal": _rounded(pv_terminal),
        "terminal_value_share": _rounded(divide(pv_terminal, enterprise_value)),
        "enterprise_value": _rounded(enterprise_value),
        "equity_value": _rounded(equity_value),
        "value_per_share": _rounded(value_per_share),
        "evidence_label": "derived_calculation",
    }


def _valid_offset_timestamp(value: Any) -> bool:
    if not isinstance(value, str) or not value.strip():
        return False
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return parsed.tzinfo is not None and parsed.utcoffset() is not None


def build_pack(raw: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise ValueError("Input must be a JSON object")
    entity = copy.deepcopy(raw.get("entity") if isinstance(raw.get("entity"), dict) else {})
    sources = copy.deepcopy(raw.get("sources") if isinstance(raw.get("sources"), list) else [])
    financials = copy.deepcopy(raw.get("financials") if isinstance(raw.get("financials"), dict) else {})
    periods = financials.get("periods") if isinstance(financials.get("periods"), list) else []
    periods = sorted((item for item in periods if isinstance(item, dict)), key=_period_sort_key)
    financials["periods"] = periods
    period_metrics = calculate_period_metrics(periods)
    latest_metrics = period_metrics[-1]["metrics"] if period_metrics else {}

    valuation_input = raw.get("valuation") if isinstance(raw.get("valuation"), dict) else {}
    market_data = valuation_input.get("market_data") if isinstance(valuation_input.get("market_data"), dict) else {}
    valuation = calculate_market_valuation(periods[-1] if periods else None, market_data)
    valuation["source_ids"] = list(valuation_input.get("source_ids") or [])
    dcf_errors: list[str] = []
    base_assumptions = valuation_input.get("dcf_assumptions")
    dcf_results: list[dict[str, Any]] = []
    if isinstance(base_assumptions, dict) and base_assumptions:
        if "base_revenue" not in base_assumptions and periods:
            base_assumptions = {**base_assumptions, "base_revenue": periods[-1].get("values", {}).get("revenue")}
        if "diluted_shares" not in base_assumptions:
            base_assumptions = {**base_assumptions, "diluted_shares": valuation["market_data"].get("diluted_shares")}
        try:
            dcf_results.append({"name": "base", **calculate_dcf(base_assumptions)})
        except ValueError as exc:
            dcf_errors.append(f"base DCF: {exc}")
        for position, scenario in enumerate(valuation_input.get("scenarios") or [], start=1):
            if not isinstance(scenario, dict):
                dcf_errors.append(f"scenario {position}: must be an object")
                continue
            name = str(scenario.get("name") or f"scenario-{position}")
            overrides = scenario.get("overrides") if isinstance(scenario.get("overrides"), dict) else {}
            try:
                dcf_results.append({"name": name, **calculate_dcf({**base_assumptions, **overrides})})
            except ValueError as exc:
                dcf_errors.append(f"{name} DCF: {exc}")
    valuation["dcf"] = dcf_results

    source_ids = [item.get("id") for item in sources if isinstance(item, dict)]
    valid_source_ids = {item for item in source_ids if isinstance(item, str) and item}
    missing: list[str] = []
    warnings: list[str] = []
    conflicts = list((raw.get("quality") or {}).get("conflicts") or []) if isinstance(raw.get("quality"), dict) else []
    if not _valid_offset_timestamp(raw.get("as_of")):
        missing.append("as_of with timezone offset")
    for field in ("name", "primary_symbol", "exchange", "country", "reporting_currency"):
        if not entity.get(field):
            missing.append(f"entity.{field}")
    if not sources:
        missing.append("sources")
    if len(valid_source_ids) != len(source_ids):
        warnings.append("source IDs must be unique, non-empty strings")
    if not periods:
        missing.append("financials.periods")
    for period in periods:
        unknown = set(period.get("source_ids") or []) - valid_source_ids
        if unknown:
            warnings.append(
                f"period {period.get('period_end') or 'unknown'} references unknown source IDs: {', '.join(sorted(unknown))}"
            )
        values = period.get("values")
        if not isinstance(values, dict) or not any(number(value) is not None for value in values.values()):
            warnings.append(f"period {period.get('period_end') or 'unknown'} has no numeric values")
        if not period.get("currency") or not period.get("unit_scale"):
            warnings.append(f"period {period.get('period_end') or 'unknown'} lacks currency or unit scale")
    if periods and not valuation["multiples"] and not dcf_results:
        warnings.append("valuation inputs are absent or insufficient")
    warnings.extend(dcf_errors)
    input_quality = raw.get("quality") if isinstance(raw.get("quality"), dict) else {}
    warnings.extend(str(item) for item in input_quality.get("warnings") or [])
    missing.extend(str(item) for item in input_quality.get("missing") or [])
    missing = list(dict.fromkeys(missing))
    warnings = list(dict.fromkeys(warnings))
    status = "blocked" if any(item in missing for item in ("sources", "financials.periods", "as_of with timezone offset")) else "limited" if missing or warnings or conflicts else "ready"

    return {
        "schema": SCHEMA,
        "schemaVersion": 1,
        "as_of": raw.get("as_of"),
        "entity": entity,
        "scope": copy.deepcopy(raw.get("scope") if isinstance(raw.get("scope"), dict) else {}),
        "sources": sources,
        "financials": financials,
        "metrics": {"periods": period_metrics, "latest": latest_metrics},
        "valuation": valuation,
        "expectations": copy.deepcopy(raw.get("expectations") if isinstance(raw.get("expectations"), dict) else {}),
        "thesis": copy.deepcopy(raw.get("thesis") if isinstance(raw.get("thesis"), dict) else {}),
        "quality": {
            "status": status,
            "missing": missing,
            "warnings": warnings,
            "conflicts": conflicts,
            "checks": [
                "source IDs",
                "as-of timezone",
                "numeric period values",
                "currency and scale presence",
                "ratio denominator safety",
                "DCF WACC/terminal-growth relationship",
            ],
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--strict", action="store_true", help="Exit 2 when readiness is blocked")
    args = parser.parse_args()
    try:
        raw = json.loads(args.input.read_text(encoding="utf-8"))
        pack = build_pack(raw)
        rendered = json.dumps(pack, indent=2, ensure_ascii=False, allow_nan=False) + "\n"
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        raise SystemExit(str(exc)) from exc
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    if args.strict and pack["quality"]["status"] == "blocked":
        raise SystemExit(2)


if __name__ == "__main__":
    main()
