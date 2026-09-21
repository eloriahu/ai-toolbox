"""Normalize and filter a portable market-event calendar from supplied JSON."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any


CATEGORIES = {"earnings", "macro", "central-bank", "dividend", "index", "ipo", "corporate", "other"}


def _timestamp(value: Any) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else None


def build_calendar(data: dict[str, Any], days: int = 14) -> dict[str, Any]:
    if not isinstance(data, dict):
        raise ValueError("Calendar input must be an object.")
    as_of = _timestamp(data.get("as_of"))
    if as_of is None:
        raise ValueError("as_of must be an ISO-8601 timestamp with an offset.")
    events = data.get("events")
    if not isinstance(events, list):
        raise ValueError("events must be an array.")
    horizon = as_of + timedelta(days=max(days, 0))
    included, invalid = [], []
    for event in events:
        if not isinstance(event, dict):
            invalid.append({"event": event, "reason": "not an object"})
            continue
        when = _timestamp(event.get("starts_at"))
        if when is None:
            invalid.append({"event": event.get("id"), "reason": "invalid starts_at"})
            continue
        category = str(event.get("category", "other"))
        if category not in CATEGORIES:
            invalid.append({"event": event.get("id"), "reason": f"unsupported category: {category}"})
            continue
        if as_of <= when <= horizon:
            item = dict(event)
            item["category"] = category
            item["hours_until"] = round((when - as_of).total_seconds() / 3600.0, 1)
            item["timing_status"] = "confirmed" if event.get("confirmed") is True else "provisional"
            included.append(item)
    included.sort(key=lambda item: item["starts_at"])
    return {
        "schemaVersion": 1,
        "asOf": data["as_of"],
        "horizonDays": days,
        "events": included,
        "invalid": invalid,
        "note": "This helper normalizes supplied events; it does not discover or verify them.",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input")
    parser.add_argument("--days", type=int, default=14)
    parser.add_argument("--output")
    args = parser.parse_args()
    data = json.loads(Path(args.input).read_text(encoding="utf-8"))
    result = build_calendar(data, args.days)
    text = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        Path(args.output).write_text(text, encoding="utf-8")
    else:
        print(text, end="")


if __name__ == "__main__":
    main()
