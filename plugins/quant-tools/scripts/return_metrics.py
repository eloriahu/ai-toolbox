"""Calculate common return and drawdown metrics from CSV or toolbox snapshot JSON."""

from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
from datetime import date, datetime
from pathlib import Path


ObservationTime = date | datetime


def calculate_metrics(
    rows: list[tuple[ObservationTime, float]],
    risk_free_rate: float = 0.0,
    periods_per_year: float = 252.0,
) -> dict:
    if len(rows) < 2:
        raise ValueError("At least two observations are required.")
    if not math.isfinite(risk_free_rate):
        raise ValueError("Risk-free rate must be finite.")
    if not math.isfinite(periods_per_year) or periods_per_year <= 0:
        raise ValueError("Periods per year must be finite and greater than zero.")

    ordered = sorted(rows, key=lambda item: item[0])
    if len({day for day, _ in ordered}) != len(ordered):
        raise ValueError("Dates must be unique.")
    if any(price <= 0 or not math.isfinite(price) for _, price in ordered):
        raise ValueError("Close values must be finite and greater than zero.")

    returns = [
        current / previous - 1
        for (_, previous), (_, current) in zip(ordered, ordered[1:])
    ]
    elapsed_days = (ordered[-1][0] - ordered[0][0]).total_seconds() / 86_400
    total_return = ordered[-1][1] / ordered[0][1] - 1
    cagr = (
        (ordered[-1][1] / ordered[0][1]) ** (365.25 / elapsed_days) - 1
        if elapsed_days > 0
        else None
    )
    daily_volatility = statistics.stdev(returns) if len(returns) > 1 else 0.0
    annualized_volatility = daily_volatility * math.sqrt(periods_per_year)
    excess_daily = statistics.fmean(returns) - risk_free_rate / periods_per_year
    sharpe = (
        excess_daily / daily_volatility * math.sqrt(periods_per_year)
        if daily_volatility > 0
        else None
    )

    peak = ordered[0][1]
    max_drawdown = 0.0
    for _, price in ordered:
        peak = max(peak, price)
        max_drawdown = min(max_drawdown, price / peak - 1)

    return {
        "startDate": ordered[0][0].isoformat(),
        "endDate": ordered[-1][0].isoformat(),
        "observations": len(ordered),
        "totalReturn": total_return,
        "cagr": cagr,
        "annualizedVolatility": annualized_volatility,
        "sharpeRatio": sharpe,
        "maxDrawdown": max_drawdown,
        "riskFreeRate": risk_free_rate,
        "periodsPerYear": periods_per_year,
    }


def read_prices(path: Path) -> list[tuple[date, float]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None or not {"date", "close"}.issubset(reader.fieldnames):
            raise ValueError("CSV must contain 'date' and 'close' columns.")
        try:
            return [
                (date.fromisoformat(row["date"].strip()), float(row["close"]))
                for row in reader
            ]
        except (TypeError, ValueError) as exc:
            raise ValueError("Dates must be ISO YYYY-MM-DD and close values numeric.") from exc


def read_market_snapshot(path: Path) -> tuple[list[tuple[datetime, float]], dict]:
    try:
        snapshot = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid market snapshot JSON: {exc}") from exc
    if not isinstance(snapshot, dict):
        raise ValueError("Market snapshot JSON must be an object.")
    if snapshot.get("schemaVersion") != 1:
        raise ValueError("Market snapshot requires schemaVersion 1.")
    raw_rows = snapshot.get("rows")
    if not isinstance(raw_rows, list):
        raise ValueError("Market snapshot requires a 'rows' array.")

    prices = []
    missing_close_rows = 0
    for position, row in enumerate(raw_rows, start=1):
        if not isinstance(row, dict):
            raise ValueError(f"Market snapshot row {position} must be an object.")
        close = row.get("close")
        if close is None:
            missing_close_rows += 1
            continue
        timestamp = row.get("timestamp")
        if not isinstance(timestamp, str) or not timestamp.strip():
            raise ValueError(
                f"Market snapshot row {position} requires a timestamp string."
            )
        try:
            observed_at = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            price = float(close)
        except (TypeError, ValueError) as exc:
            raise ValueError(
                f"Market snapshot row {position} has an invalid timestamp or close."
            ) from exc
        prices.append((observed_at, price))

    source = {
        "format": "ai-toolbox-market-snapshot-v1",
        "ticker": snapshot.get("ticker"),
        "provider": snapshot.get("provider"),
        "retrievedAt": snapshot.get("retrievedAt"),
        "interval": snapshot.get("interval"),
        "currency": snapshot.get("currency"),
        "adjustment": snapshot.get("adjustment"),
        "inputRows": len(raw_rows),
        "usedRows": len(prices),
        "missingCloseRows": missing_close_rows,
    }
    return prices, source


def read_price_file(
    path: Path, input_format: str = "auto"
) -> tuple[list[tuple[ObservationTime, float]], dict]:
    resolved_format = input_format
    if resolved_format == "auto":
        resolved_format = "market-snapshot" if path.suffix.lower() == ".json" else "csv"
    if resolved_format == "market-snapshot":
        return read_market_snapshot(path)
    if resolved_format == "csv":
        rows = read_prices(path)
        return rows, {
            "format": "date-close-csv",
            "inputRows": len(rows),
            "usedRows": len(rows),
            "missingCloseRows": 0,
        }
    raise ValueError("Input format must be auto, csv, or market-snapshot.")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("price_file", help="date/close CSV or ai-toolbox snapshot JSON")
    parser.add_argument("--output", help="Write JSON to this path instead of stdout.")
    parser.add_argument(
        "--input-format",
        choices=("auto", "csv", "market-snapshot"),
        default="auto",
    )
    parser.add_argument("--risk-free-rate", type=float, default=0.0)
    parser.add_argument(
        "--periods-per-year",
        type=float,
        default=252.0,
        help="Annualization factor matching the observation frequency (default: 252).",
    )
    args = parser.parse_args()
    try:
        rows, source = read_price_file(Path(args.price_file), args.input_format)
        result = calculate_metrics(
            rows,
            risk_free_rate=args.risk_free_rate,
            periods_per_year=args.periods_per_year,
        )
        result["source"] = source
    except (OSError, ValueError) as exc:
        raise SystemExit(str(exc)) from exc
    rendered = json.dumps(result, indent=2, allow_nan=False) + "\n"
    if args.output:
        Path(args.output).write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")


if __name__ == "__main__":
    main()
