"""Lazy, read-only adapters for optional fundamental-data integrations."""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable
from urllib.request import Request, urlopen


PROVIDERS = {
    "financetoolkit": {
        "package": "financetoolkit",
        "provider": "FinanceToolkit",
        "credential_env": ("FINANCIAL_MODELING_PREP_API_KEY", "FMP_API_KEY"),
        "authority": "calculation-engine",
    },
    "financedatabase": {
        "package": "financedatabase",
        "provider": "FinanceDatabase",
        "credential_env": (),
        "authority": "security-master",
    },
    "jquants": {
        "package": "jquantsapi",
        "provider": "J-Quants API",
        "credential_env": ("JQUANTS_API_KEY",),
        "authority": "official-exchange-service",
    },
    "opendart": {
        "package": "OpenDartReader",
        "provider": "Korea FSS OpenDART",
        "credential_env": ("DART_API_KEY",),
        "authority": "official-regulator-service",
    },
    "twse": {
        "package": None,
        "provider": "Taiwan Stock Exchange OpenAPI",
        "credential_env": (),
        "authority": "official-exchange-service",
    },
    "edgar": {
        "package": "edgar",
        "provider": "US SEC EDGAR via EdgarTools",
        "credential_env": ("EDGAR_IDENTITY",),
        "authority": "official-regulator-service",
    },
    "akshare": {
        "package": "akshare",
        "provider": "AKShare public-web adapters",
        "credential_env": (),
        "authority": "aggregator-fallback",
    },
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def capability_report() -> dict[str, Any]:
    providers = []
    for name, config in PROVIDERS.items():
        package = config["package"]
        variables = config["credential_env"]
        providers.append(
            {
                "adapter": name,
                "provider": config["provider"],
                "authority": config["authority"],
                "package": package,
                "package_available": package is None or importlib.util.find_spec(package) is not None,
                "credentials": {
                    variable: "configured" if bool(os.getenv(variable)) else "not_configured"
                    for variable in variables
                },
            }
        )
    return {
        "schema": "fundamental_adapter_capabilities/v1",
        "schemaVersion": 1,
        "checked_at": utc_now(),
        "providers": providers,
        "note": "Credential values are never inspected or returned.",
    }


def _require_package(module: str, requirement_file: str) -> None:
    if importlib.util.find_spec(module) is None:
        raise RuntimeError(
            f"Optional package '{module}' is unavailable. Install the isolated dependencies from {requirement_file}."
        )


def _require_env(*names: str) -> str:
    for name in names:
        value = os.getenv(name)
        if value:
            return value
    raise RuntimeError(f"Required credential is not configured. Set one of: {', '.join(names)}")


def _jsonable(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if hasattr(value, "isoformat"):
        try:
            return value.isoformat()
        except (TypeError, ValueError):
            pass
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    try:
        if value != value:
            return None
    except (TypeError, ValueError):
        pass
    return str(value)


def frame_payload(frame: Any) -> dict[str, Any]:
    """Preserve DataFrame indexes/columns without requiring pandas here."""
    if frame is None:
        return {"columns": [], "index": [], "data": []}
    if hasattr(frame, "to_json"):
        try:
            return json.loads(frame.to_json(orient="split", date_format="iso"))
        except (TypeError, ValueError):
            pass
    if hasattr(frame, "to_dict"):
        try:
            return {"records": _jsonable(frame.to_dict(orient="records"))}
        except (TypeError, ValueError):
            return {"data": _jsonable(frame.to_dict())}
    return {"data": _jsonable(frame)}


def envelope(
    adapter: str,
    query: dict[str, Any],
    datasets: dict[str, Any],
    *,
    endpoint: str | None = None,
    warnings: list[str] | None = None,
) -> dict[str, Any]:
    config = PROVIDERS[adapter]
    return {
        "schema": "fundamental_adapter_output/v1",
        "schemaVersion": 1,
        "adapter": adapter,
        "provider": config["provider"],
        "authority": config["authority"],
        "retrieved_at": utc_now(),
        "query": query,
        "endpoint": endpoint,
        "datasets": datasets,
        "warnings": warnings or [],
        "lineage": {
            "raw_provider_labels_preserved": True,
            "normalized_to_fundamental_pack": False,
        },
    }


def collect_financedatabase(args: argparse.Namespace) -> dict[str, Any]:
    _require_package("financedatabase", "requirements.core.lock.txt")
    import financedatabase as fd  # type: ignore[import-not-found]

    equities = fd.Equities()
    search_field = "index" if args.field == "symbol" else "name"
    frame = equities.search(**{search_field: args.query})
    if args.country and "country" in frame.columns:
        frame = frame[frame["country"].astype(str).str.casefold() == args.country.casefold()]
    if args.market and "market" in frame.columns:
        frame = frame[frame["market"].astype(str).str.casefold() == args.market.casefold()]
    frame = frame.head(args.limit)
    return envelope(
        "financedatabase",
        {"query": args.query, "field": args.field, "country": args.country, "market": args.market},
        {"equities": frame_payload(frame)},
        warnings=["Community-maintained identity metadata must be checked against the listing venue."],
    )


def collect_financetoolkit(args: argparse.Namespace) -> dict[str, Any]:
    _require_package("financetoolkit", "requirements.core.lock.txt")
    from financetoolkit import Toolkit  # type: ignore[import-not-found]

    api_key = os.getenv("FINANCIAL_MODELING_PREP_API_KEY") or os.getenv("FMP_API_KEY") or ""
    companies = Toolkit(
        tickers=[args.ticker],
        api_key=api_key,
        start_date=args.start_date,
        quarterly=args.quarterly,
        enforce_source=args.enforce_source,
        benchmark_ticker=None,
        progress_bar=False,
    )
    datasets = {
        "income_statement": frame_payload(companies.get_income_statement()),
        "balance_sheet": frame_payload(companies.get_balance_sheet_statement()),
        "cash_flow_statement": frame_payload(companies.get_cash_flow_statement()),
        "profitability_ratios": frame_payload(companies.ratios.collect_profitability_ratios()),
        "solvency_ratios": frame_payload(companies.ratios.collect_solvency_ratios()),
        "valuation_ratios": frame_payload(companies.ratios.collect_valuation_ratios()),
    }
    warnings = [
        "FinanceToolkit is a calculation/provider-routing layer; preserve its underlying FMP, Yahoo or user-data lineage."
    ]
    if not api_key:
        warnings.append("No FMP credential was configured; FinanceToolkit may use its documented fallback source.")
    return envelope(
        "financetoolkit",
        {
            "ticker": args.ticker,
            "start_date": args.start_date,
            "quarterly": args.quarterly,
            "enforce_source": args.enforce_source,
        },
        datasets,
        warnings=warnings,
    )


def collect_jquants(args: argparse.Namespace) -> dict[str, Any]:
    _require_package("jquantsapi", "requirements.jp.lock.txt")
    api_key = _require_env("JQUANTS_API_KEY")
    import jquantsapi  # type: ignore[import-not-found]

    client = jquantsapi.ClientV2(api_key=api_key)
    summary, summary_cursor = client.get_fin_summary_cursor(code=args.code, date_yyyymmdd=args.date or "")
    details, details_cursor = client.get_fin_details_cursor(code=args.code, date_yyyymmdd=args.date or "")
    valuation = client.get_eq_valuation(code=args.code, date_yyyymmdd=args.date or "")
    return envelope(
        "jquants",
        {"code": args.code, "date": args.date},
        {
            "financial_summary": frame_payload(summary),
            "financial_details": frame_payload(details),
            "valuation": frame_payload(valuation),
            "cursors_present": {"summary": bool(summary_cursor), "details": bool(details_cursor)},
        },
        endpoint="J-Quants API v2: /fins/summary, /fins/details, /equities/valuation",
    )


def collect_opendart(args: argparse.Namespace) -> dict[str, Any]:
    _require_package("OpenDartReader", "requirements.kr.lock.txt")
    api_key = _require_env("DART_API_KEY")
    import OpenDartReader  # type: ignore[import-not-found]

    reader = OpenDartReader.OpenDartReader(api_key)
    statements = reader.finstate(args.corp, args.year, reprt_code=args.report_code)
    detailed = reader.finstate_all(args.corp, args.year, reprt_code=args.report_code, fs_div=args.fs_div)
    return envelope(
        "opendart",
        {"corp": args.corp, "year": args.year, "report_code": args.report_code, "fs_div": args.fs_div},
        {"financial_summary": frame_payload(statements), "financial_details": frame_payload(detailed)},
        endpoint="Korea FSS OpenDART financial statement APIs",
    )


TWSE_ENDPOINTS = {
    "income": "/opendata/t187ap06_L_{industry}",
    "balance": "/opendata/t187ap07_L_{industry}",
    "monthly-revenue": "/opendata/t187ap05_L",
    "profitability": "/opendata/t187ap17_L",
}


def collect_twse(args: argparse.Namespace) -> dict[str, Any]:
    template = TWSE_ENDPOINTS[args.statement]
    path = template.format(industry=args.industry)
    url = f"https://openapi.twse.com.tw/v1{path}"
    request = Request(url, headers={"User-Agent": "ai-toolbox-fundamental-tools/0.1"})
    with urlopen(request, timeout=args.timeout) as response:  # nosec B310 - fixed HTTPS host
        rows = json.load(response)
    if not isinstance(rows, list):
        raise RuntimeError("TWSE response was not a JSON array")
    filtered = [
        row
        for row in rows
        if isinstance(row, dict)
        and str(row.get("公司代號") or row.get("Code") or "").strip() == args.code
    ]
    return envelope(
        "twse",
        {"code": args.code, "statement": args.statement, "industry": args.industry},
        {"records": filtered},
        endpoint=url,
        warnings=[
            "Most TWSE OpenAPI datasets are current snapshots rather than arbitrary historical queries.",
            "Statement formats are industry-specific; verify the selected industry suffix.",
        ],
    )


def collect_edgar(args: argparse.Namespace) -> dict[str, Any]:
    _require_package("edgar", "requirements.us.lock.txt")
    identity = _require_env("EDGAR_IDENTITY")
    from edgar import Company, set_identity  # type: ignore[import-not-found]

    set_identity(identity)
    company = Company(args.ticker)
    financials = company.get_financials()
    datasets = {
        "income_statement": frame_payload(financials.income_statement().to_dataframe()),
        "balance_sheet": frame_payload(financials.balance_sheet().to_dataframe()),
        "cash_flow_statement": frame_payload(financials.cashflow_statement().to_dataframe()),
    }
    return envelope(
        "edgar",
        {"ticker": args.ticker},
        datasets,
        endpoint="US SEC EDGAR company filings/XBRL",
        warnings=["Use for SEC registrants and ADRs; it is not the primary filing source for a local APAC listing."],
    )


def collect_akshare(args: argparse.Namespace) -> dict[str, Any]:
    _require_package("akshare", "requirements.cn.lock.txt")
    import akshare as ak  # type: ignore[import-not-found]

    statement_names = ("资产负债表", "利润表", "现金流量表")
    if args.market == "HK":
        datasets = {
            name: frame_payload(ak.stock_financial_hk_report_em(stock=args.symbol, symbol=name, indicator=args.period))
            for name in statement_names
        }
        datasets["analysis_indicators"] = frame_payload(
            ak.stock_financial_hk_analysis_indicator_em(symbol=args.symbol, indicator=args.period)
        )
    else:
        datasets = {
            name: frame_payload(ak.stock_financial_report_sina(stock=args.symbol, symbol=name))
            for name in statement_names
        }
    return envelope(
        "akshare",
        {"symbol": args.symbol, "market": args.market, "period": args.period},
        datasets,
        warnings=[
            "Fallback aggregator: retain the underlying website named by AKShare and verify material figures against official filings.",
            "Public-web endpoints can change without notice.",
        ],
    )


def _write(result: dict[str, Any], output: Path | None) -> None:
    rendered = json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False) + "\n"
    if output:
        output.write_text(rendered, encoding="utf-8")
    else:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8")
        sys.stdout.write(rendered)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    capabilities = subparsers.add_parser("capabilities")
    capabilities.set_defaults(handler=lambda _: capability_report())

    database = subparsers.add_parser("financedatabase")
    database.add_argument("--query", required=True)
    database.add_argument("--field", choices=("symbol", "name"), default="symbol")
    database.add_argument("--country")
    database.add_argument("--market")
    database.add_argument("--limit", type=int, default=20)
    database.set_defaults(handler=collect_financedatabase)

    toolkit = subparsers.add_parser("financetoolkit")
    toolkit.add_argument("--ticker", required=True)
    toolkit.add_argument("--start-date")
    toolkit.add_argument("--quarterly", action="store_true")
    toolkit.add_argument("--enforce-source", choices=("FinancialModelingPrep", "YahooFinance"))
    toolkit.set_defaults(handler=collect_financetoolkit)

    jquants = subparsers.add_parser("jquants")
    jquants.add_argument("--code", required=True)
    jquants.add_argument("--date")
    jquants.set_defaults(handler=collect_jquants)

    dart = subparsers.add_parser("opendart")
    dart.add_argument("--corp", required=True)
    dart.add_argument("--year", type=int, required=True)
    dart.add_argument("--report-code", default="11011")
    dart.add_argument("--fs-div", choices=("CFS", "OFS"), default="CFS")
    dart.set_defaults(handler=collect_opendart)

    twse = subparsers.add_parser("twse")
    twse.add_argument("--code", required=True)
    twse.add_argument("--statement", choices=tuple(TWSE_ENDPOINTS), default="income")
    twse.add_argument("--industry", choices=("ci", "basi", "fh", "ins", "bd", "mim"), default="ci")
    twse.add_argument("--timeout", type=float, default=30.0)
    twse.set_defaults(handler=collect_twse)

    edgar = subparsers.add_parser("edgar")
    edgar.add_argument("--ticker", required=True)
    edgar.set_defaults(handler=collect_edgar)

    akshare = subparsers.add_parser("akshare")
    akshare.add_argument("--symbol", required=True)
    akshare.add_argument("--market", choices=("CN", "HK"), default="CN")
    akshare.add_argument("--period", choices=("年度", "报告期"), default="年度")
    akshare.set_defaults(handler=collect_akshare)

    for child in subparsers.choices.values():
        child.add_argument("--output", type=Path)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    try:
        result = args.handler(args)
        _write(result, args.output)
    except (RuntimeError, OSError, ValueError, KeyError, TypeError) as exc:
        raise SystemExit(str(exc)) from exc


if __name__ == "__main__":
    main()
