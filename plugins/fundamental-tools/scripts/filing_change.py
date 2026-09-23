"""Conservative, source-linked comparison of two extracted filings."""

from __future__ import annotations

import argparse
import difflib
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any


SCHEMA = "filing_change/v1"


def _dated(value: str) -> datetime:
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if result.tzinfo is None:
        raise ValueError("Filing timestamps must include a timezone offset")
    return result


def _sections(document: dict[str, Any]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for section in document.get("sections", []):
        key = str(section.get("key") or "").strip()
        if not key or key in result:
            raise ValueError("Section keys must be nonempty and unique within each filing")
        if not str(section.get("text") or "").strip():
            raise ValueError(f"Section {key} has no extracted text")
        result[key] = section
    return result


def compare(payload: dict[str, Any]) -> dict[str, Any]:
    old = payload["prior"]
    new = payload["current"]
    if old.get("issuer") != new.get("issuer") or not old.get("issuer"):
        raise ValueError("Prior and current filings must identify the same issuer")
    if old.get("filing_type") != new.get("filing_type") or not old.get("filing_type"):
        raise ValueError("Compare the same filing type; supply an explicit mapping for a changed taxonomy")
    if _dated(old["published_at"]) >= _dated(new["published_at"]):
        raise ValueError("Current filing must be published after the prior filing")
    for document in (old, new):
        if not document.get("source_id") or not document.get("source_url"):
            raise ValueError("Each filing needs a source ID and source URL")
    prior = _sections(old)
    current = _sections(new)
    changes: list[dict[str, Any]] = []
    for key in sorted(prior.keys() | current.keys()):
        before = prior.get(key)
        after = current.get(key)
        left = re.sub(r"\s+", " ", str(before.get("text", ""))).strip() if before else ""
        right = re.sub(r"\s+", " ", str(after.get("text", ""))).strip() if after else ""
        if left == right:
            continue
        status = "added" if before is None else "removed" if after is None else "changed"
        old_numbers = re.findall(r"(?<!\w)[+-]?\d[\d,]*(?:\.\d+)?%?", left)
        new_numbers = re.findall(r"(?<!\w)[+-]?\d[\d,]*(?:\.\d+)?%?", right)
        changes.append({
            "section_key": key,
            "heading": (after or before).get("heading", key),
            "status": status,
            "similarity": round(difflib.SequenceMatcher(None, left, right, autojunk=False).ratio(), 4),
            "prior": None if before is None else {"text": left, "page": before.get("page"), "source_id": old["source_id"]},
            "current": None if after is None else {"text": right, "page": after.get("page"), "source_id": new["source_id"]},
            "numbers_changed": old_numbers != new_numbers,
            "review_status": "analyst_review_required",
        })
    gaps = []
    if not prior or not current:
        gaps.append("One filing has no extracted sections")
    if any(s.get("page") is None for s in [*prior.values(), *current.values()]):
        gaps.append("Some section page references are unavailable")
    return {
        "schema": SCHEMA, "schemaVersion": 1, "issuer": old["issuer"],
        "filing_type": old["filing_type"],
        "prior": {k: old[k] for k in ("source_id", "source_url", "published_at")},
        "current": {k: new[k] for k in ("source_id", "source_url", "published_at")},
        "changes": changes,
        "quality": {"status": "limited" if gaps else "ready", "gaps": gaps,
                    "warning": "Text and number changes are review flags, not a materiality or causal judgment."},
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
