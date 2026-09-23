"""Normalize APAC investor flows and disclosed holdings without conflating them."""

from __future__ import annotations

import argparse
import json
import os
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen


SCHEMA = "ownership_flow/v1"
FINMIND_URL = "https://api.finmindtrade.com/api/v4/data"


def _decimal(raw: Any) -> Decimal:
    if raw is None or isinstance(raw, bool):
        raise ValueError("Missing numeric value")
    try:
        value = Decimal(str(raw).replace(",", ""))
    except InvalidOperation as exc:
        raise ValueError(f"Invalid numeric value: {raw}") from exc
    if not value.is_finite():
        raise ValueError("Non-finite numeric value")
    return value


def _iso_date(raw: str) -> str:
    return date.fromisoformat(raw).isoformat()


def build(payload: dict[str, Any]) -> dict[str, Any]:
    if not payload.get("symbol") or payload.get("market") not in {"TW", "KR", "HK", "JP", "CN", "AU", "IN", "SG"}:
        raise ValueError("Supply a symbol and supported APAC market")
    as_of = payload.get("as_of") or datetime.now(timezone.utc).isoformat()
    observed_at = datetime.fromisoformat(as_of.replace("Z", "+00:00"))
    if observed_at.tzinfo is None:
        raise ValueError("Pack as_of must include a timezone offset")
    flows = []
    for item in payload.get("flows", []):
        if not item.get("source_id") or not item.get("investor_category") or not item.get("unit"):
            raise ValueError("Each flow needs source, investor category and unit")
        buy = _decimal(item["buy"]) if item.get("buy") is not None else None
        sell = _decimal(item["sell"]) if item.get("sell") is not None else None
        if buy is not None and buy < 0 or sell is not None and sell < 0:
            raise ValueError("Buy and sell totals must be nonnegative")
        net = _decimal(item["net"]) if item.get("net") is not None else None
        if buy is not None and sell is not None:
            computed = buy - sell
            if net is not None and net != computed:
                raise ValueError("Net flow does not equal buy minus sell")
            net = computed
        if net is None:
            raise ValueError("Supply net flow or both buy and sell")
        flows.append({
            "date": _iso_date(item["date"]), "investor_category": item["investor_category"],
            "buy": str(buy) if buy is not None else None,
            "sell": str(sell) if sell is not None else None,
            "net": str(net), "unit": item["unit"], "source_id": item["source_id"],
            "source_url": item.get("source_url"), "provider": item.get("provider"),
        })
    holdings = []
    for item in payload.get("holdings", []):
        if not item.get("source_id") or not item.get("holder") or not item.get("ownership_type"):
            raise ValueError("Each holding needs source, holder and ownership type")
        stake = _decimal(item["stake_percent"])
        if stake < 0 or stake > 100:
            raise ValueError("Stake percent must be between 0 and 100")
        holdings.append({
            "holder": item["holder"], "stake_percent": str(stake),
            "ownership_type": item["ownership_type"], "as_of": _iso_date(item["as_of"]),
            "filed_at": item.get("filed_at"), "source_id": item["source_id"],
            "source_url": item.get("source_url"),
        })
    gaps = []
    if not flows:
        gaps.append("No investor-flow observations")
    if not holdings:
        gaps.append("No disclosed ownership observations")
    return {
        "schema": SCHEMA, "schemaVersion": 1, "market": payload["market"],
        "symbol": payload["symbol"], "as_of": as_of,
        "flows": flows, "holdings": holdings,
        "quality": {"status": "limited" if gaps else "ready", "gaps": gaps,
                    "warning": "Trading flows are not ownership changes; category flows do not identify beneficial owners or explain price moves."},
    }


def fetch_finmind(symbol: str, start: str, end: str) -> dict[str, Any]:
    token = os.getenv("FINMIND_TOKEN")
    if not token:
        raise RuntimeError("FINMIND_TOKEN is required; credential values are never stored")
    if date.fromisoformat(start) > date.fromisoformat(end):
        raise ValueError("Start date must be no later than end date")
    params = urlencode({"dataset": "TaiwanStockInstitutionalInvestorsBuySell", "data_id": symbol,
                        "start_date": start, "end_date": end})
    request = Request(f"{FINMIND_URL}?{params}", headers={"Authorization": f"Bearer {token}",
                                                       "User-Agent": "ai-toolbox-fundamental-tools/1"})
    with urlopen(request, timeout=25) as response:
        raw = json.load(response)
    if raw.get("status") != 200 or not isinstance(raw.get("data"), list):
        raise RuntimeError(f"FinMind request failed (status {raw.get('status')}); check token and entitlement")
    rows = []
    for row in raw["data"]:
        if str(row.get("stock_id")) != symbol:
            continue
        rows.append({"date": row["date"], "investor_category": row["name"],
                     "buy": row["buy"], "sell": row["sell"], "unit": "shares",
                     "source_id": f"finmind:{symbol}:{row['date']}:{row['name']}",
                     "source_url": f"{FINMIND_URL}?{params}", "provider": "FinMind"})
    return build({"market": "TW", "symbol": symbol, "flows": rows, "holdings": [],
                  "as_of": datetime.now(timezone.utc).isoformat()})


def fetch_pykrx(symbol: str, start: str, end: str) -> dict[str, Any]:
    try:
        from pykrx import stock  # type: ignore[import-not-found]
    except ImportError as exc:
        raise RuntimeError("pykrx is optional; install it separately before using the Korea adapter") from exc
    if date.fromisoformat(start) > date.fromisoformat(end):
        raise ValueError("Start date must be no later than end date")
    frame = stock.get_market_trading_value_by_date(start.replace("-", ""), end.replace("-", ""), symbol)
    rows = []
    for day, values in frame.iterrows():
        day_text = day.date().isoformat() if hasattr(day, "date") else _iso_date(str(day)[:10])
        for category, net in values.items():
            if str(category) == "전체":
                continue
            rows.append({"date": day_text, "investor_category": str(category),
                         "net": str(net), "unit": "KRW", "provider": "pykrx/KRX",
                         "source_id": f"pykrx:{symbol}:{day_text}:{category}"})
    return build({"market": "KR", "symbol": symbol, "flows": rows, "holdings": [],
                  "as_of": datetime.now(timezone.utc).isoformat()})


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    supplied = sub.add_parser("build", help="Normalize supplied flow and disclosed-ownership observations")
    supplied.add_argument("input", type=Path)
    supplied.add_argument("--output", type=Path)
    for name in ("finmind", "pykrx"):
        adapter = sub.add_parser(name)
        adapter.add_argument("--symbol", required=True)
        adapter.add_argument("--start", required=True)
        adapter.add_argument("--end", required=True)
        adapter.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.command == "build":
        result = build(json.loads(args.input.read_text(encoding="utf-8")))
    elif args.command == "finmind":
        result = fetch_finmind(args.symbol, args.start, args.end)
    else:
        result = fetch_pykrx(args.symbol, args.start, args.end)
    rendered = json.dumps(result, indent=2, ensure_ascii=False) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")


if __name__ == "__main__":
    main()
