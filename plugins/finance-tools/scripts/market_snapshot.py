"""Return a small, reproducible yfinance snapshot as JSON."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("ticker", help="Yahoo Finance ticker, for example 7203.T or 9988.HK")
    parser.add_argument("--period", default="1mo")
    parser.add_argument("--interval", default="1d")
    args = parser.parse_args()

    try:
        import yfinance as yf
    except ImportError as exc:
        raise SystemExit(
            "yfinance is not installed. Install plugins/finance-tools/requirements.lock.txt first."
        ) from exc

    history = yf.Ticker(args.ticker).history(period=args.period, interval=args.interval)
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

    result = {
        "ticker": args.ticker,
        "provider": "Yahoo Finance via yfinance",
        "retrievedAt": datetime.now(timezone.utc).isoformat(),
        "period": args.period,
        "interval": args.interval,
        "rowCount": len(rows),
        "rows": rows,
    }
    print(json.dumps(result, indent=2, allow_nan=False))


def _number(value):
    if value is None:
        return None
    try:
        if value != value:
            return None
        return value.item() if hasattr(value, "item") else value
    except TypeError:
        return None


if __name__ == "__main__":
    main()
