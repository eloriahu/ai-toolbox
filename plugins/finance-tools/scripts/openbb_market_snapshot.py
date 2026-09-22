"""Fetch a timestamped OpenBB quote basket or APAC exchange snapshot."""

from __future__ import annotations

import argparse
import json
import re
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


APAC_MARKETS = {
    "AU": ["asx"],
    "CN": ["shh", "shz"],
    "HK": ["hkse"],
    "ID": ["jkt"],
    "IN": ["nse"],
    "JP": ["jpx"],
    "KR": ["koe", "ksc"],
    "MY": ["kls"],
    "NZ": ["nze"],
    "SG": ["ses"],
    "TH": ["set"],
    "TW": ["tai", "two"],
}

ZONE_BY_SUFFIX = {
    ".AX": "Australia/Sydney", ".HK": "Asia/Hong_Kong", ".JK": "Asia/Jakarta",
    ".KL": "Asia/Kuala_Lumpur", ".KS": "Asia/Seoul", ".KQ": "Asia/Seoul",
    ".NS": "Asia/Kolkata", ".NZ": "Pacific/Auckland", ".SI": "Asia/Singapore",
    ".SS": "Asia/Shanghai", ".SZ": "Asia/Shanghai", ".T": "Asia/Tokyo",
    ".TW": "Asia/Taipei", ".TWO": "Asia/Taipei",
}
ZONE_BY_MARKET = {
    "AU": "Australia/Sydney", "CN": "Asia/Shanghai", "HK": "Asia/Hong_Kong",
    "ID": "Asia/Jakarta", "IN": "Asia/Kolkata", "JP": "Asia/Tokyo",
    "KR": "Asia/Seoul", "MY": "Asia/Kuala_Lumpur", "NZ": "Pacific/Auckland",
    "SG": "Asia/Singapore", "TH": "Asia/Bangkok", "TW": "Asia/Taipei",
    "HKG": "Asia/Hong_Kong", "JPX": "Asia/Tokyo", "KSC": "Asia/Seoul",
}

# Windows Python installations do not always bundle the IANA timezone database.
# These markets do not observe daylight saving, so a fixed offset is an honest
# fallback. Sydney and Auckland intentionally have no fixed fallback: a naive
# observation stays naive rather than being assigned the wrong seasonal offset.
FIXED_OFFSET_MINUTES = {
    "Asia/Bangkok": 7 * 60,
    "Asia/Hong_Kong": 8 * 60,
    "Asia/Jakarta": 7 * 60,
    "Asia/Kolkata": 5 * 60 + 30,
    "Asia/Kuala_Lumpur": 8 * 60,
    "Asia/Seoul": 9 * 60,
    "Asia/Shanghai": 8 * 60,
    "Asia/Singapore": 8 * 60,
    "Asia/Taipei": 8 * 60,
    "Asia/Tokyo": 9 * 60,
}


def _timezone_for(zone_name: str):
    try:
        return ZoneInfo(zone_name)
    except ZoneInfoNotFoundError:
        offset = FIXED_OFFSET_MINUTES.get(zone_name)
        return timezone(timedelta(minutes=offset)) if offset is not None else None


def _record(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return dict(value)
    if hasattr(value, "model_dump"):
        return value.model_dump()
    if hasattr(value, "dict"):
        return value.dict()
    raise TypeError(f"Unsupported OpenBB result row: {type(value).__name__}")


def normalize_symbols(symbols: list[str], provider: str) -> list[str]:
    if provider.lower() != "yfinance":
        return symbols
    result = []
    for symbol in symbols:
        match = re.fullmatch(r"(\d{1,4})\.HK", symbol.upper())
        result.append(f"{int(match.group(1)):04d}.HK" if match else symbol)
    return result


def _timestamp(value: Any, *, symbol: str | None, market: str | None) -> str | None:
    if value is None:
        return None
    if not isinstance(value, datetime):
        try:
            value = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except ValueError:
            return str(value)
    if value.utcoffset() is None:
        zone_name = ZONE_BY_MARKET.get(market or "")
        if symbol:
            zone_name = next((zone for suffix, zone in ZONE_BY_SUFFIX.items() if symbol.upper().endswith(suffix)), zone_name)
        if zone_name:
            resolved_zone = _timezone_for(zone_name)
            if resolved_zone is not None:
                value = value.replace(tzinfo=resolved_zone)
    return value.isoformat()


def _delay_minutes(timestamp: str | None, reference: datetime) -> float | None:
    if timestamp is None:
        return None
    try:
        observed = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    except ValueError:
        return None
    if observed.utcoffset() is None:
        return None
    return round((reference - observed.astimezone(timezone.utc)).total_seconds() / 60, 1)


def normalize_results(
    records: list[Any],
    *,
    provider: str,
    market: str | None,
    requested_at: datetime,
    completed_at: datetime,
) -> dict[str, Any]:
    quotes = []
    for value in records:
        row = _record(value)
        last = row.get("last_price", row.get("close"))
        timestamp = _timestamp(
            row.get("last_price_timestamp", row.get("last_timestamp", row.get("date"))),
            symbol=row.get("symbol"),
            market=market,
        )
        quotes.append({
            key: item for key, item in {
                "symbol": row.get("symbol"),
                "name": row.get("name"),
                "market": market or row.get("exchange"),
                "exchange": row.get("exchange"),
                "currency": row.get("currency"),
                "last": last,
                "prev_close": row.get("prev_close"),
                "pct_change": row.get("change_percent"),
                "open": row.get("open"),
                "high": row.get("high"),
                "low": row.get("low"),
                "volume": row.get("volume"),
                "timestamp": timestamp,
            }.items() if item is not None
        })
    timestamps = sorted(str(row["timestamp"]) for row in quotes if row.get("timestamp"))
    return {
        "schemaVersion": 1,
        "provider": f"{provider} via OpenBB",
        "source_kind": "openbb_fallback",
        "market": market,
        "requested_at": requested_at.isoformat(),
        "completed_at": completed_at.isoformat(),
        "data_as_of": timestamps[-1] if timestamps else None,
        "capture_window": {"start": timestamps[0] if timestamps else None, "end": timestamps[-1] if timestamps else None},
        "movement_basis": "latest_vs_previous_close",
        "quotes": quotes,
        "quality": {
            "row_count": len(quotes),
            "timestamp_verified": bool(timestamps),
            "provider_delay_minutes": _delay_minutes(timestamps[-1], completed_at) if timestamps else None,
        },
    }


def attach_latest_bars(pack: dict[str, Any], records: list[Any]) -> dict[str, Any]:
    latest: dict[str, dict[str, Any]] = {}
    market_by_symbol = {
        str(row.get("symbol") or "").upper(): row.get("market") or row.get("exchange") or pack.get("market")
        for row in pack.get("quotes", [])
    }
    for value in records:
        row = _record(value)
        symbol = str(row.get("symbol") or "").upper()
        observed = _timestamp(row.get("date"), symbol=symbol, market=market_by_symbol.get(symbol) or pack.get("market"))
        if not symbol or observed is None:
            continue
        candidate = {"timestamp": observed, "last": row.get("close")}
        if symbol not in latest or observed > latest[symbol]["timestamp"]:
            latest[symbol] = candidate
    for row in pack.get("quotes", []):
        bar = latest.get(str(row.get("symbol") or "").upper())
        if bar:
            row.update({key: value for key, value in bar.items() if value is not None})
    timestamps = sorted(str(row["timestamp"]) for row in pack.get("quotes", []) if row.get("timestamp"))
    pack["data_as_of"] = timestamps[-1] if timestamps else None
    pack["capture_window"] = {"start": timestamps[0] if timestamps else None, "end": timestamps[-1] if timestamps else None}
    pack["quality"]["timestamp_verified"] = bool(timestamps)
    completed_at = datetime.fromisoformat(str(pack["completed_at"]).replace("Z", "+00:00"))
    pack["quality"]["provider_delay_minutes"] = _delay_minutes(timestamps[-1], completed_at) if timestamps else None
    return pack


def _results(response: Any) -> list[Any]:
    results = getattr(response, "results", None)
    if results is None and isinstance(response, dict):
        results = response.get("results")
    return list(results or [])


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    selection = parser.add_mutually_exclusive_group(required=True)
    selection.add_argument("--markets", help="Comma-separated APAC country codes, or APAC")
    selection.add_argument("--symbols", help="Comma-separated provider symbols")
    parser.add_argument("--provider", default="fmp")
    parser.add_argument("--output")
    args = parser.parse_args()
    try:
        from openbb import obb
    except ImportError as exc:
        raise SystemExit("OpenBB is not installed. Install plugins/finance-tools/requirements.lock.txt in an isolated environment.") from exc

    started = datetime.now(timezone.utc)
    packs = []
    if args.symbols:
        symbols = normalize_symbols([item.strip() for item in args.symbols.split(",") if item.strip()], args.provider)
        response = obb.equity.price.quote(symbol=symbols, provider=args.provider)
        pack = normalize_results(_results(response), provider=args.provider, market=None, requested_at=started, completed_at=datetime.now(timezone.utc))
        if args.provider.lower() == "yfinance" and not pack["quality"]["timestamp_verified"]:
            bars = obb.equity.price.historical(
                symbol=symbols,
                interval="1m",
                start_date=(date.today() - timedelta(days=5)).isoformat(),
                provider="yfinance",
            )
            attach_latest_bars(pack, _results(bars))
        packs.append(pack)
    else:
        requested_codes = list(APAC_MARKETS) if args.markets.upper() == "APAC" else [item.strip().upper() for item in args.markets.split(",") if item.strip()]
        unknown = [code for code in requested_codes if code not in APAC_MARKETS]
        if unknown:
            raise SystemExit(f"Unknown APAC market code(s): {', '.join(unknown)}")
        for code in requested_codes:
            for exchange in APAC_MARKETS[code]:
                query_started = datetime.now(timezone.utc)
                response = obb.equity.market_snapshots(market=exchange, provider=args.provider)
                packs.append(normalize_results(_results(response), provider=args.provider, market=code, requested_at=query_started, completed_at=datetime.now(timezone.utc)))

    result = {"schemaVersion": 1, "provider": f"{args.provider} via OpenBB", "requested_at": started.isoformat(), "packs": packs}
    rendered = json.dumps(result, indent=2, ensure_ascii=False, default=str, allow_nan=False) + "\n"
    if args.output:
        Path(args.output).write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")


if __name__ == "__main__":
    main()
