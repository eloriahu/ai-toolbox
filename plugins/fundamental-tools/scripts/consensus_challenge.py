"""Build a conservative, auditable sell-side consensus challenge pack."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any


SCHEMA = "consensus_challenge/v1"
STANCES = {"supports", "opposes", "neutral"}
COUNTER_STATES = {"candidate", "primary_checked", "refuted"}


def _pick(item: dict[str, Any], fields: tuple[str, ...]) -> dict[str, Any]:
    """Export metadata and concise claims, never unknown raw-report fields."""
    return {field: item[field] for field in fields if field in item}


def _concise(value: Any, label: str, limit: int = 1200) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > limit:
        raise ValueError(f"{label} must be a concise nonempty text field (at most {limit} characters)")
    return value.strip()


def _timestamp(value: Any, label: str) -> datetime:
    if not isinstance(value, str):
        raise ValueError(f"{label} needs an offset timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{label} needs an ISO timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"{label} needs a timezone offset")
    return parsed


def _unique(items: Any, label: str) -> dict[str, dict[str, Any]]:
    if not isinstance(items, list):
        raise ValueError(f"{label} must be a list")
    result = {}
    for item in items:
        if not isinstance(item, dict) or not isinstance(item.get("id"), str) or not item["id"].strip():
            raise ValueError(f"{label} IDs must be nonempty strings")
        if item["id"] in result:
            raise ValueError(f"Duplicate {label} ID: {item['id']}")
        result[item["id"]] = item
    return result


def _source_ids(ids: Any, sources: dict[str, dict[str, Any]], label: str) -> list[str]:
    if not isinstance(ids, list) or any(not isinstance(item, str) for item in ids):
        raise ValueError(f"{label} source_ids must be a list of strings")
    unknown = set(ids) - sources.keys()
    if unknown:
        raise ValueError(f"{label} cites unknown sources: {', '.join(sorted(unknown))}")
    return list(dict.fromkeys(ids))


def _house_groups(raw: Any) -> dict[str, str]:
    houses = _unique(raw, "eligible_houses")
    result = {}
    for house_id, house in houses.items():
        group = str(house.get("group") or house_id).strip()
        if not group:
            raise ValueError("Each eligible house needs a group")
        result[house_id] = group
    return result


def _latest_views(
    views: list[dict[str, Any]], thesis_id: str, as_of: datetime,
    cutoff: datetime, groups: dict[str, str], sources: dict[str, dict[str, Any]],
    counter_ids: set[str],
) -> tuple[list[dict[str, Any]], int]:
    latest: dict[str, dict[str, Any]] = {}
    stale = 0
    for view in views:
        if view.get("thesis_id") != thesis_id:
            continue
        house_id = view.get("house_id")
        if not isinstance(house_id, str) or not house_id:
            raise ValueError("Every view needs house_id")
        if view.get("stance") not in STANCES:
            raise ValueError(f"Invalid stance for {house_id}")
        published = _timestamp(view.get("published_at"), f"view {house_id}")
        if published > as_of:
            raise ValueError(f"View {house_id} is dated after pack as_of")
        source_id = view.get("source_id")
        if source_id not in sources:
            raise ValueError(f"View {house_id} needs a known report source")
        if sources[source_id].get("house_id") != house_id:
            raise ValueError(f"View {house_id} needs a house-specific report source")
        if _timestamp(sources[source_id]["published_at"], f"report {source_id}") > published:
            raise ValueError(f"View {house_id} predates its report source")
        basis_ids = _source_ids(view.get("basis_source_ids", []), sources, f"view {house_id}")
        addressed = view.get("addressed_counterevidence_ids", [])
        if not isinstance(addressed, list) or any(not isinstance(item, str) for item in addressed) or set(addressed) - counter_ids:
            raise ValueError(f"View {house_id} has unknown addressed counterevidence")
        if published < cutoff:
            stale += 1
            continue
        group = groups.get(house_id, house_id)
        normalized = {**view, "house_group": group, "basis_source_ids": basis_ids,
                      "addressed_counterevidence_ids": addressed, "_published": published}
        prior = latest.get(group)
        if prior is None or published > prior["_published"]:
            latest[group] = normalized
        elif published == prior["_published"] and view["stance"] != prior["stance"]:
            raise ValueError(f"Conflicting simultaneous views from house group {group}")
    return list(latest.values()), stale


def build(payload: dict[str, Any]) -> dict[str, Any]:
    as_of = _timestamp(payload.get("as_of"), "as_of")
    entity = payload.get("entity")
    if not isinstance(entity, dict) or not entity.get("name") or not entity.get("primary_symbol"):
        raise ValueError("Entity needs name and primary_symbol")
    window_days = payload.get("window_days", 90)
    if isinstance(window_days, bool) or not isinstance(window_days, int) or not 1 <= window_days <= 730:
        raise ValueError("window_days must be an integer from 1 to 730")
    minimum = payload.get("minimum_supporting_groups", 3)
    if isinstance(minimum, bool) or not isinstance(minimum, int) or minimum < 3:
        raise ValueError("minimum_supporting_groups must be at least 3")
    cutoff = as_of - timedelta(days=window_days)
    sources = _unique(payload.get("sources", []), "sources")
    for source_id, source in sources.items():
        if not source.get("origin") or not source.get("independence_group"):
            raise ValueError(f"Source {source_id} needs origin and independence_group")
        _concise(source["origin"], f"source {source_id} origin", 500)
        if _timestamp(source.get("published_at"), f"source {source_id}") > as_of:
            raise ValueError(f"Source {source_id} is dated after pack as_of")
    house_groups = _house_groups(payload.get("eligible_houses", []))
    eligible_groups = set(house_groups.values())
    universe_basis = str(payload.get("universe_basis") or "").strip()
    if universe_basis:
        _concise(universe_basis, "universe_basis")
    theses = _unique(payload.get("theses", []), "theses")
    if not theses:
        raise ValueError("At least one explicitly stated thesis is required")
    premises: dict[str, dict[str, Any]] = {}
    for thesis_id, thesis in theses.items():
        if not thesis.get("statement") or not thesis.get("horizon") or thesis.get("direction") not in {"bullish", "bearish"}:
            raise ValueError(f"Thesis {thesis_id} needs statement, horizon and bullish/bearish direction")
        _concise(thesis["statement"], f"thesis {thesis_id} statement")
        if not isinstance(thesis.get("premises"), list) or not thesis["premises"]:
            raise ValueError(f"Thesis {thesis_id} needs premises")
        for premise in thesis["premises"]:
            if not isinstance(premise, dict) or not premise.get("id") or not premise.get("statement"):
                raise ValueError(f"Thesis {thesis_id} has an incomplete premise")
            _concise(premise["statement"], f"premise {premise['id']} statement")
            if premise["id"] in premises:
                raise ValueError(f"Duplicate premise ID: {premise['id']}")
            _source_ids(premise.get("source_ids", []), sources, f"premise {premise['id']}")
            premises[premise["id"]] = {**premise, "thesis_id": thesis_id}
    counters = _unique(payload.get("counterevidence", []), "counterevidence")
    for counter_id, counter in counters.items():
        if counter.get("premise_id") not in premises or not counter.get("statement"):
            raise ValueError(f"Counterevidence {counter_id} needs a known premise and statement")
        _concise(counter["statement"], f"counterevidence {counter_id} statement")
        if counter.get("status") not in COUNTER_STATES:
            raise ValueError(f"Counterevidence {counter_id} needs candidate, primary_checked or refuted status")
        if not _source_ids(counter.get("source_ids", []), sources, f"counterevidence {counter_id}"):
            raise ValueError(f"Counterevidence {counter_id} needs source IDs")
    views = payload.get("views", [])
    if not isinstance(views, list):
        raise ValueError("views must be a list")
    for view in views:
        if not isinstance(view, dict) or view.get("thesis_id") not in theses:
            raise ValueError("Every view needs a known thesis_id")
        if view.get("horizon") != theses[view["thesis_id"]]["horizon"]:
            raise ValueError("A view horizon must match the thesis horizon before counting agreement")
        if not isinstance(view.get("premise_ids", []), list) or any(
            premise_id not in premises or premises[premise_id]["thesis_id"] != view["thesis_id"]
            for premise_id in view.get("premise_ids", [])
        ):
            raise ValueError("View premise_ids must belong to its thesis")
        if view.get("stance") == "supports" and not view.get("premise_ids"):
            raise ValueError("A supporting view needs at least one mapped thesis premise")
    analyses = []
    challenges = []
    for thesis_id, thesis in theses.items():
        current_views, stale_count = _latest_views(views, thesis_id, as_of, cutoff, house_groups, sources, set(counters))
        counted = [view for view in current_views if not eligible_groups or view["house_group"] in eligible_groups]
        supporters = [view for view in counted if view["stance"] == "supports"]
        denominator = len(eligible_groups) if eligible_groups else None
        gate = "unverified_universe"
        if denominator and universe_basis:
            gate = "established" if len(supporters) >= minimum and len(supporters) * 2 > denominator else "not_established"
        basis_counter: Counter[str] = Counter()
        for view in supporters:
            basis_counter.update({sources[source_id]["independence_group"] for source_id in view["basis_source_ids"]})
        analyses.append({
            "thesis_id": thesis_id, "statement": thesis["statement"],
            "direction": thesis["direction"], "horizon": thesis["horizon"],
            "mainstream_gate": {"state": gate, "eligible_house_groups": denominator,
                                "fresh_observed_groups": len(counted),
                                "supporting_groups": len(supporters),
                                "opposing_groups": sum(view["stance"] == "opposes" for view in counted),
                                "neutral_groups": sum(view["stance"] == "neutral" for view in counted),
                                "stale_reports_excluded": stale_count,
                                "support_share_of_universe": None if not denominator else str(Decimal(len(supporters)) / Decimal(denominator)),
                                "rule": "Strict majority of the declared eligible house groups and at least the minimum supporting groups; one latest fresh view per group."},
            "supporting_house_groups": sorted(view["house_group"] for view in supporters),
            "shared_basis_groups": [{"independence_group": group, "supporting_views": count}
                                    for group, count in sorted(basis_counter.items(), key=lambda item: (-item[1], item[0]))],
        })
        for premise in thesis["premises"]:
            premise_id = premise["id"]
            aligned = [view for view in supporters if premise_id in view.get("premise_ids", [])]
            linked = [counter for counter in counters.values() if counter["premise_id"] == premise_id]
            checked = [counter for counter in linked if counter["status"] == "primary_checked"]
            all_full_text = bool(supporters) and all(view.get("reviewed_full_text") is True for view in supporters)
            unaddressed = [counter["id"] for counter in checked
                           if all(counter["id"] not in view["addressed_counterevidence_ids"] for view in supporters)]
            gaps = []
            if not premise.get("source_ids"):
                gaps.append("premise has no direct supporting source")
            if not str(premise.get("falsifier") or "").strip():
                gaps.append("premise has no explicit falsifier")
            if not all_full_text:
                gaps.append("not all supporting reports were reviewed in full")
            challenges.append({
                "thesis_id": thesis_id, "premise_id": premise_id,
                "premise": premise["statement"],
                "supporting_house_groups_using_premise": sorted(view["house_group"] for view in aligned),
                "premise_source_ids": premise.get("source_ids", []),
                "falsifier": premise.get("falsifier"),
                "counterevidence_ids": [counter["id"] for counter in linked],
                "primary_checked_counterevidence_ids": [counter["id"] for counter in checked],
                "unaddressed_in_reviewed_sample_ids": unaddressed if all_full_text else [],
                "coverage_state": "full_text_sample" if all_full_text else "partial_or_unknown",
                "priority": "test_now" if all_full_text and unaddressed else "investigate",
                "gaps": gaps, "novelty_status": "not_established",
            })
    established_ids = {item["thesis_id"] for item in analyses if item["mainstream_gate"]["state"] == "established"}
    quality_gaps = []
    if not eligible_groups or not universe_basis:
        quality_gaps.append("No documented eligible large-house universe; convergence is observed-only")
    if not established_ids:
        quality_gaps.append("No thesis passes the declared mainstream gate")
    if not counters:
        quality_gaps.append("No sourced counterevidence supplied")
    elif not any(item["status"] == "primary_checked" and premises[item["premise_id"]]["thesis_id"] in established_ids
                 for item in counters.values()):
        quality_gaps.append("No primary-checked counterevidence for an established mainstream thesis is supplied")
    if any(item["coverage_state"] != "full_text_sample" for item in challenges):
        quality_gaps.append("Not all supporting reports were reviewed in full; absence of discussion cannot be assessed")
    return {
        "schema": SCHEMA, "schemaVersion": 1, "as_of": payload["as_of"],
        "entity": entity, "window_days": window_days,
        "universe_basis": universe_basis or None,
        "eligible_houses": [_pick(item, ("id", "name", "group")) for item in payload.get("eligible_houses", [])],
        "sources": [_pick(item, ("id", "origin", "independence_group", "published_at", "source_type", "url", "house_id", "access_note"))
                    for item in sources.values()],
        "theses": [{**_pick(item, ("id", "statement", "direction", "horizon")),
                    "premises": [_pick(premise, ("id", "statement", "source_ids", "falsifier"))
                                 for premise in item["premises"]]} for item in theses.values()],
        "views": [_pick(item, ("house_id", "thesis_id", "horizon", "stance", "published_at", "source_id",
                               "premise_ids", "basis_source_ids", "reviewed_full_text",
                               "addressed_counterevidence_ids")) for item in views],
        "counterevidence": [_pick(item, ("id", "premise_id", "statement", "source_ids", "status"))
                            for item in counters.values()],
        "analyses": analyses, "challenge_queue": challenges,
        "quality": {"status": "limited" if quality_gaps else "ready", "gaps": quality_gaps,
                    "warning": "This pack identifies testable weaknesses in sampled reports; it cannot establish that a flaw is novel, causal, or an investment opportunity. Verify all source content independently."},
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    payload = json.loads(args.input.read_text(encoding="utf-8"))
    result = build(payload)
    rendered = json.dumps(result, indent=2, ensure_ascii=False) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")


if __name__ == "__main__":
    main()
