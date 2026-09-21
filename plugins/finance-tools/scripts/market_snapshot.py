"""Return a small, provenance-rich yfinance snapshot as JSON."""

from __future__ import annotations

import argparse
import json
import math
from datetime import datetime, timezone
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("ticker", help="Yahoo Finance ticker, for example 7203.T or 9988.HK")
    parser.add_argument("--period", default="1mo")
    parser.add_argument("--interval", default="1d")
    parser.add_argument("--output", help="Write JSON to this path instead of stdout.")
    parser.add_argument(
        "--auto-adjust",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Adjust OHLC values for splits and dividends (default: true).",
    )
    args = parser.parse_args()

    try:
        import yfinance as yf
    except ImportError as exc:
        raise SystemExit(
            "yfinance is not installed. Install plugins/finance-tools/requirements.lock.txt first."
        ) from exc

    ticker = yf.Ticker(args.ticker)
    history = ticker.history(
        period=args.period,
        interval=args.interval,
        auto_adjust=args.auto_adjust,
        actions=False,
    )
    metadata = getattr(ticker, "history_metadata", None)
    if not isinstance(metadata, dict):
        metadata = {}

    result = build_snapshot(
        ticker=args.ticker,
        period=args.period,
        interval=args.interval,
        auto_adjust=args.auto_adjust,
        history=history,
        metadata=metadata,
    )
    rendered = json.dumps(result, indent=2, allow_nan=False) + "\n"
    if args.output:
        Path(args.output).write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")


def build_snapshot(
    *,
    ticker: str,
    period: str,
    interval: str,
    auto_adjust: bool,
    history,
    metadata: dict,
    retrieved_at: datetime | None = None,
) -> dict:
    rows = []
    for index, row in history.iterrows():
        rows.append(
            {
                "timestamp": index.isoformat(),
                "open": _number(row.get("Open")),
                "high": _number(row.get("High")),
                "low": _number(row.get("Low")),
                "close": _number(row.get("Close")),
                "volume": _number(row.get("Volume")),
            }
        )

    fields = ("open", "high", "low", "close", "volume")
    missing_by_field = {
        field: sum(row[field] is None for row in rows) for field in fields
    }
    currency = _optional_text(metadata.get("currency"))
    exchange_timezone = _optional_text(metadata.get("exchangeTimezoneName"))

    return {
        "schemaVersion": 1,
        "ticker": ticker,
        "provider": "Yahoo Finance via yfinance",
        "retrievedAt": (retrieved_at or datetime.now(timezone.utc)).isoformat(),
        "period": period,
        "interval": interval,
        "currency": currency,
        "exchangeTimezone": exchange_timezone,
        "adjustment": {
            "autoAdjusted": auto_adjust,
            "corporateActionsIncluded": False,
        },
        "rowCount": len(rows),
        "missingData": {
            "empty": not rows,
            "currencyUnavailable": currency is None,
            "exchangeTimezoneUnavailable": exchange_timezone is None,
            "nullValuesByField": missing_by_field,
        },
        "rows": rows,
    }


def _number(value):
    if value is None:
        return None
    try:
        if value != value:
            return None
        number = value.item() if hasattr(value, "item") else value
        if isinstance(number, float) and not math.isfinite(number):
            return None
        return number
    except (TypeError, ValueError):
        return None


def _optional_text(value) -> str | None:
    return value.strip() if isinstance(value, str) and value.strip() else None


if __name__ == "__main__":
    main()
