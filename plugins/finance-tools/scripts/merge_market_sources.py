"""Merge a preferred user-supplied market pack with a fallback provider pack."""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any


LIVE_FIELDS = {"last", "prev_close", "pct_change", "open", "high", "low", "volume", "turnover", "timestamp"}


def _parse(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed if parsed.utcoffset() is not None else None
    except ValueError:
        return None


def _empty(value: Any) -> bool:
    return value is None or value == "" or value == [] or value == {}


def _canonical_symbol(value: Any) -> str | None:
    """Map common Bloomberg equity tickers to their public-provider form."""
    if value is None:
        return None
    symbol = str(value).strip().upper()
    if not symbol:
        return None
    hk_public = re.fullmatch(r"(\d+)\.HK", symbol)
    if hk_public:
        return f"{hk_public.group(1).zfill(4)}.HK"

    match = re.fullmatch(r"(.+?)\s+(HK|JP|KS|KQ|AU|SP|TT|CH|IN|TB|IJ|MK|PM)\s+EQUITY", symbol)
    if not match:
        return symbol

    code, market = match.groups()
    suffixes = {
        "JP": ".T",
        "KS": ".KS",
        "KQ": ".KQ",
        "AU": ".AX",
        "SP": ".SI",
        "TT": ".TW",
        "IN": ".NS",
        "TB": ".BK",
        "IJ": ".JK",
        "MK": ".KL",
        "PM": ".PS",
    }
    if market == "HK":
        return f"{code.zfill(4)}.HK" if code.isdigit() else f"{code}.HK"
    if market == "CH":
        return f"{code}.SS" if code.startswith(("5", "6", "9")) else f"{code}.SZ"
    return f"{code}{suffixes[market]}"


def _identity(row: dict[str, Any]) -> str | None:
    value = row.get("symbol") or row.get("name")
    return _canonical_symbol(value)


def _fresh(row: dict[str, Any], expected: datetime | None, max_age_minutes: int) -> bool | None:
    observed = _parse(row.get("timestamp"))
    if expected is None or observed is None:
        return None
    return (expected - observed).total_seconds() / 60 <= max_age_minutes


def merge_packs(
    primary: dict[str, Any],
    fallback: dict[str, Any],
    *,
    expected_market_timestamp: str | None = None,
    max_age_minutes: int = 5,
) -> dict[str, Any]:
    expected = _parse(expected_market_timestamp)
    fallback_rows = {_identity(row): row for row in fallback.get("quotes", []) if _identity(row)}
    output_rows = []
    conflicts = []
    fallback_fields = []
    seen = set()

    for primary_row in primary.get("quotes", []):
        key = _identity(primary_row)
        if key is None:
            continue
        seen.add(key)
        backup = fallback_rows.get(key, {})
        primary_fresh = _fresh(primary_row, expected, max_age_minutes)
        fallback_fresh = _fresh(backup, expected, max_age_minutes)
        merged = dict(primary_row)
        lineage = {field: primary.get("provider", "primary") for field in primary_row if not _empty(primary_row[field])}
        merged["symbol"] = key
        for field, fallback_value in backup.items():
            if _empty(fallback_value):
                continue
            replace_stale_live = field in LIVE_FIELDS and primary_fresh is False and fallback_fresh is True
            if _empty(merged.get(field)) or replace_stale_live:
                merged[field] = fallback_value
                lineage[field] = fallback.get("provider", "fallback")
                fallback_fields.append({"symbol": key, "field": field, "reason": "stale_primary" if replace_stale_live else "missing_primary"})
            elif field in LIVE_FIELDS and merged.get(field) != fallback_value:
                conflicts.append({"symbol": key, "field": field, "primary": merged.get(field), "fallback": fallback_value})
        merged["lineage"] = lineage
        output_rows.append(merged)

    for key, row in fallback_rows.items():
        if key in seen:
            continue
        appended = dict(row)
        appended["symbol"] = key
        appended["lineage"] = {field: fallback.get("provider", "fallback") for field, value in row.items() if not _empty(value)}
        output_rows.append(appended)
        fallback_fields.append({"symbol": key, "field": "row", "reason": "missing_primary_row"})

    return {
        "schemaVersion": 1,
        "provider_policy": "user_supplied_bloomberg_then_openbb",
        "primary_provider": primary.get("provider"),
        "fallback_provider": fallback.get("provider"),
        "expected_market_timestamp": expected_market_timestamp,
        "movement_basis": primary.get("movement_basis") or fallback.get("movement_basis"),
        "quotes": output_rows,
        "fallback_fields": fallback_fields,
        "conflicts": conflicts,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("primary")
    parser.add_argument("fallback")
    parser.add_argument("--expected-market-timestamp")
    parser.add_argument("--max-age-minutes", type=int, default=5)
    parser.add_argument("--output")
    args = parser.parse_args()
    primary = json.loads(Path(args.primary).read_text(encoding="utf-8"))
    fallback = json.loads(Path(args.fallback).read_text(encoding="utf-8"))
    result = merge_packs(
        primary,
        fallback,
        expected_market_timestamp=args.expected_market_timestamp,
        max_age_minutes=args.max_age_minutes,
    )
    rendered = json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False) + "\n"
    if args.output:
        Path(args.output).write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")


if __name__ == "__main__":
    main()
