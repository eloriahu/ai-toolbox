"""Compare dated, like-for-like consensus or model estimate snapshots."""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any


SCHEMA = "expectations_bridge/v1"
KEY_FIELDS = ("metric", "fiscal_period", "basis", "currency", "unit", "statistic")


def _date(value: str) -> datetime:
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if result.tzinfo is None:
        raise ValueError("Snapshot as_of must include a timezone offset")
    return result


def _value(raw: Any) -> Decimal:
    if isinstance(raw, bool) or raw is None:
        raise ValueError("Estimate value must be a finite decimal")
    try:
        number = Decimal(str(raw).replace(",", ""))
    except InvalidOperation as exc:
        raise ValueError(f"Invalid estimate value: {raw}") from exc
    if not number.is_finite():
        raise ValueError("Estimate value must be finite")
    return number


def _rows(snapshot: dict[str, Any]) -> dict[tuple[str, ...], dict[str, Any]]:
    result: dict[tuple[str, ...], dict[str, Any]] = {}
    for row in snapshot.get("estimates", []):
        key = tuple(str(row.get(field) or "").strip() for field in KEY_FIELDS)
        if any(not item for item in key):
            raise ValueError("Every estimate needs metric, fiscal period, basis, currency, unit and statistic")
        if key in result:
            raise ValueError(f"Duplicate estimate key: {key}")
        if not row.get("source_ids"):
            raise ValueError(f"Estimate {key} needs source IDs")
        _value(row.get("value"))
        result[key] = row
    return result


def compare(payload: dict[str, Any]) -> dict[str, Any]:
    prior = payload["prior"]
    current = payload["current"]
    if not prior.get("issuer") or prior["issuer"] != current.get("issuer"):
        raise ValueError("Snapshots must identify the same issuer")
    if not prior.get("listing") or prior["listing"] != current.get("listing"):
        raise ValueError("Snapshots must use the same listing")
    if not prior.get("provider") or prior["provider"] != current.get("provider"):
        raise ValueError("Different providers must not be presented as estimate revisions")
    if _date(prior["as_of"]) >= _date(current["as_of"]):
        raise ValueError("Current snapshot must be later than prior snapshot")
    before = _rows(prior)
    after = _rows(current)
    changes = []
    for key in sorted(before.keys() | after.keys()):
        old = before.get(key)
        new = after.get(key)
        status = "new" if old is None else "dropped" if new is None else "comparable"
        old_value = _value(old["value"]) if old else None
        new_value = _value(new["value"]) if new else None
        delta = new_value - old_value if old_value is not None and new_value is not None else None
        percent = delta / abs(old_value) * 100 if delta is not None and old_value != 0 else None
        changes.append({
            **dict(zip(KEY_FIELDS, key)), "status": status,
            "prior_value": str(old_value) if old_value is not None else None,
            "current_value": str(new_value) if new_value is not None else None,
            "absolute_change": str(delta) if delta is not None else None,
            "percent_change": str(percent) if percent is not None else None,
            "prior_source_ids": old.get("source_ids", []) if old else [],
            "current_source_ids": new.get("source_ids", []) if new else [],
        })
    comparable = sum(row["status"] == "comparable" for row in changes)
    gaps = []
    if not before or not after:
        gaps.append("One snapshot has no estimates")
    if not comparable:
        gaps.append("No like-for-like estimate rows overlap")
    return {
        "schema": SCHEMA, "schemaVersion": 1, "issuer": prior["issuer"],
        "listing": prior["listing"], "provider": prior["provider"],
        "prior_as_of": prior["as_of"], "current_as_of": current["as_of"],
        "changes": changes,
        "quality": {"status": "limited" if gaps else "ready", "gaps": gaps,
                    "warning": "A revision is not an earnings surprise or a price-reaction attribution."},
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = compare(json.loads(args.input.read_text(encoding="utf-8")))
    rendered = json.dumps(result, indent=2, ensure_ascii=False) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")


if __name__ == "__main__":
    main()
