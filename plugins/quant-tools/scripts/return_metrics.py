"""Calculate common return and drawdown metrics from a date/close CSV."""

from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
from datetime import date
from pathlib import Path


def calculate_metrics(rows: list[tuple[date, float]], risk_free_rate: float = 0.0) -> dict:
    if len(rows) < 2:
        raise ValueError("At least two observations are required.")

    ordered = sorted(rows, key=lambda item: item[0])
    if len({day for day, _ in ordered}) != len(ordered):
        raise ValueError("Dates must be unique.")
    if any(price <= 0 or not math.isfinite(price) for _, price in ordered):
        raise ValueError("Close values must be finite and greater than zero.")

    returns = [
        current / previous - 1
        for (_, previous), (_, current) in zip(ordered, ordered[1:])
    ]
    elapsed_days = (ordered[-1][0] - ordered[0][0]).days
    total_return = ordered[-1][1] / ordered[0][1] - 1
    cagr = (
        (ordered[-1][1] / ordered[0][1]) ** (365.25 / elapsed_days) - 1
        if elapsed_days > 0
        else None
    )
    daily_volatility = statistics.stdev(returns) if len(returns) > 1 else 0.0
    annualized_volatility = daily_volatility * math.sqrt(252)
    excess_daily = statistics.fmean(returns) - risk_free_rate / 252
    sharpe = (
        excess_daily / daily_volatility * math.sqrt(252)
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


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("csv_file")
    parser.add_argument("--risk-free-rate", type=float, default=0.0)
    args = parser.parse_args()
    try:
        result = calculate_metrics(
            read_prices(Path(args.csv_file)), risk_free_rate=args.risk_free_rate
        )
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc
    print(json.dumps(result, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
