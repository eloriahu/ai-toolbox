"""Build and validate the dependency-free ``research_review/v1`` contract."""

from __future__ import annotations

import argparse
import copy
import json
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any


SCHEMA = "research_review/v1"
LANE_STATES = {"complete", "partial", "missing", "not_applicable"}
LANE_VALUES = {
    "complete": Decimal("1"),
    "partial": Decimal("0.5"),
    "missing": Decimal("0"),
}
PROMISE_STATES = {"delivered", "partial", "missed", "pending", "withdrawn", "unclear"}
PROMISE_OPERATORS = {"gt", "gte", "lt", "lte", "eq", "between"}
DRIFT_CLASSES = ("fact", "price", "wording")
CONCLUSION_EFFECTS = {"strengthened", "weakened", "falsified", "unchanged", "unclear"}
AUDIT_STATES = {"pass", "fail", "unverifiable"}


def _decimal(value: Any) -> Decimal | None:
    """Parse a finite decimal exactly, avoiding binary float comparisons."""
    if value is None or isinstance(value, (bool, float)):
        return None
    text = str(value).strip().replace(",", "")
    if not text or text.lower() in {"n/a", "na", "nan", "none", "null", "-"}:
        return None
    negative = text.startswith("(") and text.endswith(")")
    percent = text.endswith("%")
    text = text.strip("()").replace("%", "")
    try:
        result = Decimal(text)
    except InvalidOperation:
        return None
    if negative:
        result = -result
    if percent:
        result /= Decimal("100")
    return result if result.is_finite() else None


def _decimal_text(value: Decimal | None) -> str | None:
    if value is None:
        return None
    rendered = format(value, "f")
    if "." in rendered:
        rendered = rendered.rstrip("0").rstrip(".")
    return rendered or "0"


def _json_default(value: Any) -> str:
    if isinstance(value, Decimal):
        return format(value, "f")
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")


def _valid_offset_timestamp(value: Any) -> bool:
    if not isinstance(value, str) or not value.strip():
        return False
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return parsed.tzinfo is not None and parsed.utcoffset() is not None


def _as_of_date(value: Any) -> date | None:
    if not _valid_offset_timestamp(value):
        return None
    return datetime.fromisoformat(str(value).replace("Z", "+00:00")).date()


def _parse_date(value: Any) -> date | None:
    if not isinstance(value, str):
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def _known_sources(sources: list[dict[str, Any]]) -> tuple[set[str], list[str]]:
    ids = [item.get("id") for item in sources if isinstance(item, dict)]
    valid_ids = [item for item in ids if isinstance(item, str) and item.strip()]
    known: set[str] = set()
    issues = (
        []
        if len(ids) == len(valid_ids) and len(valid_ids) == len(set(valid_ids))
        else ["source IDs must be unique, non-empty strings"]
    )
    for item in sources:
        if not isinstance(item, dict) or not item.get("id"):
            continue
        if not item.get("origin"):
            issues.append(f"source {item['id']} requires its direct upstream origin")
        if not item.get("independence_group"):
            issues.append(f"source {item['id']} requires an independence_group")
        source_id = item.get("id")
        if (
            isinstance(source_id, str)
            and source_id.strip()
            and valid_ids.count(source_id) == 1
            and item.get("origin")
            and item.get("independence_group")
        ):
            known.add(source_id)
    return known, issues


def _build_claims(
    raw: Any,
    known_sources: set[str],
) -> tuple[list[dict[str, Any]], list[str]]:
    claims = copy.deepcopy(raw if isinstance(raw, list) else [])
    seen: set[str] = set()
    issues: list[str] = []
    for position, value in enumerate(claims, start=1):
        if not isinstance(value, dict):
            issues.append(f"claim {position} must be an object")
            continue
        raw_claim_id = value.get("id")
        claim_id = raw_claim_id.strip() if isinstance(raw_claim_id, str) else ""
        if not claim_id or claim_id in seen:
            issues.append("claim IDs must be unique, non-empty strings")
            continue
        seen.add(claim_id)
        if not value.get("statement"):
            issues.append(f"claim {claim_id} requires a statement")
        issues.extend(_source_issues(value.get("source_ids"), known_sources, f"claim {claim_id}"))
    return claims, issues


def _source_issues(source_ids: Any, known: set[str], location: str, required: bool = True) -> list[str]:
    values = source_ids if isinstance(source_ids, list) else []
    issues: list[str] = []
    if required and not values:
        issues.append(f"{location} requires source_ids")
    invalid = [item for item in values if not isinstance(item, str) or not item.strip()]
    if invalid:
        issues.append(f"{location} source_ids must contain only non-empty strings")
    unknown = {item for item in values if isinstance(item, str) and item not in known}
    if unknown:
        issues.append(f"{location} references unknown source IDs: {', '.join(sorted(map(str, unknown)))}")
    return issues


def _string_ids(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str) and item.strip()]


def assess_researchability(
    raw: Any,
    known_sources: set[str],
) -> tuple[dict[str, Any], list[str]]:
    """Grade evidence availability, not company quality or investment merit."""
    data = copy.deepcopy(raw) if isinstance(raw, dict) else {}
    lanes = data.get("lanes") if isinstance(data.get("lanes"), list) else []
    issues: list[str] = []
    normalized: list[dict[str, Any]] = []
    earned = Decimal("0")
    possible = Decimal("0")
    required_missing: list[str] = []
    if not lanes:
        issues.append("researchability requires at least one evidence lane")
    for position, value in enumerate(lanes, start=1):
        lane = copy.deepcopy(value) if isinstance(value, dict) else {}
        name = str(lane.get("name") or f"lane-{position}")
        state = str(lane.get("state") or "missing")
        required = bool(lane.get("required", True))
        weight = _decimal(lane.get("weight", 1))
        if state not in LANE_STATES:
            issues.append(f"researchability lane {name} has invalid state {state!r}")
            state = "missing"
        if weight is None or weight < 0:
            issues.append(f"researchability lane {name} requires a non-negative weight")
            weight = Decimal("1")
        lane["name"] = name
        lane["state"] = state
        lane["required"] = required
        lane["weight"] = _decimal_text(weight)
        effective_state = state
        if state != "not_applicable":
            possible += weight
            lineage_issues = _source_issues(
                lane.get("source_ids"),
                known_sources,
                f"researchability lane {name}",
                required=state != "missing",
            )
            issues.extend(lineage_issues)
            if state in {"complete", "partial"} and lineage_issues:
                effective_state = "missing"
            earned += LANE_VALUES[effective_state] * weight
        lane["effective_state"] = effective_state
        lane["lineage_valid"] = state == "not_applicable" or effective_state == state
        if required and effective_state == "missing":
            required_missing.append(name)
            issues.append(f"required researchability lane {name} is missing or invalid")
        normalized.append(lane)
    coverage = earned / possible if possible > 0 else Decimal("0")
    if coverage >= Decimal("0.8") and not required_missing:
        grade, confidence = "A", "high"
    elif coverage >= Decimal("0.5") and known_sources:
        grade, confidence = "B", "medium"
    else:
        grade, confidence = "C", "low"
    return (
        {
            "grade": grade,
            "maximum_supported_confidence": confidence,
            "coverage": _decimal_text(coverage.quantize(Decimal("0.0001"))),
            "required_missing": required_missing,
            "lanes": normalized,
            "note": "This grades evidence availability, not the attractiveness of the security.",
        },
        issues,
    )


def _compare_promise(measurement: dict[str, Any]) -> tuple[str | None, str | None]:
    operator = str(measurement.get("operator") or "")
    actual = _decimal(measurement.get("actual"))
    if operator not in PROMISE_OPERATORS or actual is None:
        return None, None
    threshold = _decimal(measurement.get("target"))
    lower = _decimal(measurement.get("lower"))
    upper = _decimal(measurement.get("upper"))
    if operator == "between":
        if lower is None or upper is None or lower > upper:
            return None, "between requires valid lower and upper bounds"
        passed = lower <= actual <= upper
    else:
        if threshold is None:
            return None, "numeric promise requires a target"
        comparisons = {
            "gt": lambda: actual > threshold,
            "gte": lambda: actual >= threshold,
            "lt": lambda: actual < threshold,
            "lte": lambda: actual <= threshold,
            "eq": lambda: actual == threshold,
        }
        passed = comparisons[operator]()
    return "delivered" if passed else "missed", None


def build_management_ledger(
    raw: Any,
    known_sources: set[str],
    review_date: date | None,
) -> tuple[list[dict[str, Any]], list[str]]:
    output: list[dict[str, Any]] = []
    issues: list[str] = []
    for position, value in enumerate(raw if isinstance(raw, list) else [], start=1):
        item = copy.deepcopy(value) if isinstance(value, dict) else {}
        item_id = str(item.get("id") or f"promise-{position}")
        item["id"] = item_id
        issues.extend(_source_issues(item.get("source_ids"), known_sources, f"management promise {item_id}"))
        if not item.get("statement") or not _parse_date(item.get("made_at")):
            issues.append(f"management promise {item_id} requires statement and ISO made_at date")
        due_at = _parse_date(item.get("due_at"))
        measurement = item.get("measurement") if isinstance(item.get("measurement"), dict) else {}
        override = item.get("status_override")
        status: str
        determination = "deterministic_numeric_test"
        if override is not None:
            status = str(override)
            determination = "explicit_analyst_assessment"
            if status not in PROMISE_STATES:
                issues.append(f"management promise {item_id} has invalid status_override {status!r}")
                status = "unclear"
            assessment = item.get("assessment") if isinstance(item.get("assessment"), dict) else {}
            assessment_issues = _source_issues(
                assessment.get("source_ids"),
                known_sources,
                f"management promise {item_id} outcome assessment",
            )
            if not assessment.get("rationale"):
                assessment_issues.append(
                    f"management promise {item_id} outcome assessment requires rationale"
                )
            issues.extend(assessment_issues)
            if assessment_issues:
                status = "unclear"
                determination = "insufficient_outcome_evidence"
        else:
            status_result, comparison_error = _compare_promise(measurement)
            if comparison_error:
                issues.append(f"management promise {item_id}: {comparison_error}")
            if status_result:
                outcome_issues = _source_issues(
                    measurement.get("source_ids"),
                    known_sources,
                    f"management promise {item_id} measured outcome",
                )
                issues.extend(outcome_issues)
                if outcome_issues:
                    status = "unclear"
                    determination = "insufficient_outcome_evidence"
                elif status_result == "missed" and due_at and review_date and due_at > review_date:
                    status = "pending"
                    determination = "deadline_not_reached"
                else:
                    status = status_result
            elif due_at and review_date and due_at > review_date:
                status = "pending"
                determination = "deadline_not_reached"
            else:
                status = "unclear"
                determination = "insufficient_measurement"
        item["status"] = status
        item["determination"] = determination
        output.append(item)
    return output, issues


def _json_equal(left: Any, right: Any) -> bool:
    return json.dumps(
        left, sort_keys=True, ensure_ascii=False, default=_json_default
    ) == json.dumps(
        right, sort_keys=True, ensure_ascii=False, default=_json_default
    )


def _diff_mapping(classification: str, prior: Any, current: Any) -> list[dict[str, Any]]:
    prior_map = prior if isinstance(prior, dict) else {}
    current_map = current if isinstance(current, dict) else {}
    changes: list[dict[str, Any]] = []
    for key in sorted(set(prior_map) | set(current_map)):
        before = prior_map.get(key)
        after = current_map.get(key)
        if not _json_equal(before, after):
            changes.append(
                {
                    "classification": classification,
                    "path": key,
                    "before": copy.deepcopy(before),
                    "after": copy.deepcopy(after),
                }
            )
    return changes


def classify_thesis_drift(raw: Any, known_sources: set[str] | None = None) -> dict[str, Any]:
    data = raw if isinstance(raw, dict) else {}
    prior = data.get("prior") if isinstance(data.get("prior"), dict) else {}
    current = data.get("current") if isinstance(data.get("current"), dict) else {}
    baseline_present = bool(prior)
    changes: list[dict[str, Any]] = []
    changes.extend(_diff_mapping("fact", prior.get("facts"), current.get("facts")))
    changes.extend(_diff_mapping("price", prior.get("prices"), current.get("prices")))
    changes.extend(_diff_mapping("wording", prior.get("wording"), current.get("wording")))
    classes = [name for name in DRIFT_CLASSES if any(item["classification"] == name for item in changes)]
    primary = next((name for name in DRIFT_CLASSES if name in classes), "no_change")
    if "fact" in classes:
        substantive_state = "facts_changed"
    elif "price" in classes:
        substantive_state = "valuation_changed"
    else:
        substantive_state = "unchanged"
    validation_issues: list[str] = []
    known = known_sources or set()
    for change in changes:
        if change["classification"] != "fact":
            continue
        after = change.get("after")
        source_ids = after.get("source_ids") if isinstance(after, dict) else None
        validation_issues.extend(
            _source_issues(
                source_ids,
                known,
                f"changed thesis fact {change['path']}",
                required=True,
            )
        )
    raw_effect = data.get("effect_on_conclusion")
    if isinstance(raw_effect, dict):
        effect = copy.deepcopy(raw_effect)
    elif substantive_state == "unchanged":
        effect = {
            "direction": "unchanged",
            "rationale": "No operating fact or price/valuation input changed.",
            "source_ids": [],
        }
    else:
        effect = {"direction": "unclear", "rationale": None, "source_ids": []}
    if effect.get("direction") not in CONCLUSION_EFFECTS:
        validation_issues.append("effect_on_conclusion.direction is invalid")
        effect["direction"] = "unclear"
    if substantive_state != "unchanged":
        if not effect.get("rationale"):
            validation_issues.append("effect_on_conclusion requires rationale for a substantive change")
        validation_issues.extend(
            _source_issues(
                effect.get("source_ids"),
                known,
                "effect_on_conclusion",
                required=True,
            )
        )
    return {
        "primary_class": primary,
        "classes": classes,
        "substantive_state": substantive_state,
        "comparison_status": "complete" if baseline_present else "limited_no_baseline",
        "changes": changes,
        "prior_as_of": data.get("prior_as_of"),
        "current_as_of": data.get("current_as_of"),
        "validation_issues": validation_issues,
        "effect_on_conclusion": effect,
        "note": "Fact changes take precedence over price changes, which take precedence over wording-only changes.",
    }


def _metadata_mismatches(report: dict[str, Any], source: dict[str, Any]) -> list[str]:
    mismatches: list[str] = []
    for field in ("currency", "unit", "period", "basis"):
        left = report.get(field)
        right = source.get(field)
        if left is not None and right is not None and str(left) != str(right):
            mismatches.append(field)
    return mismatches


def _missing_audit_metadata(report: dict[str, Any], source: dict[str, Any]) -> list[str]:
    missing: list[str] = []
    for side_name, side in (("report", report), ("source", source)):
        for field in ("currency", "unit", "period", "basis"):
            value = side.get(field)
            if not isinstance(value, str) or not value.strip():
                missing.append(f"{side_name}.{field}")
        scale = _decimal(side.get("scale"))
        if scale is None or scale <= 0:
            missing.append(f"{side_name}.scale")
    return missing


def _positive_integral(value: Any) -> int | None:
    parsed = _decimal(value)
    if parsed is None or parsed < 1 or parsed != parsed.to_integral_value():
        return None
    return int(parsed)


def audit_numbers(
    raw: Any,
    known_sources: set[str],
    source_registry: dict[str, dict[str, Any]] | None = None,
) -> tuple[dict[str, Any], list[str]]:
    rows: list[dict[str, Any]] = []
    issues: list[str] = []
    registry = source_registry or {}
    if isinstance(raw, dict):
        values = raw.get("rows") if isinstance(raw.get("rows"), list) else []
        required = bool(raw.get("required", True))
        raw_critical_fields = raw.get("critical_fields")
        if isinstance(raw_critical_fields, list):
            critical_fields = [
                item.strip()
                for item in raw_critical_fields
                if isinstance(item, str) and item.strip()
            ]
            if len(critical_fields) != len(raw_critical_fields) or len(critical_fields) != len(
                set(critical_fields)
            ):
                issues.append("critical_fields must contain unique, non-empty strings")
        else:
            critical_fields = []
            if raw_critical_fields is not None:
                issues.append("critical_fields must be an array")
        default_minimum_independence = _positive_integral(
            raw.get("minimum_independent_sources", 1)
        )
        independence_configuration_valid = default_minimum_independence is not None
        if default_minimum_independence is None:
            issues.append("minimum_independent_sources must be a positive integer")
            default_minimum_independence = 1
    else:
        values = raw if isinstance(raw, list) else []
        required = bool(values)
        critical_fields = []
        default_minimum_independence = 1
        independence_configuration_valid = True
    if required and not critical_fields:
        issues.append("required number audit must declare every critical field in critical_fields")
    seen_row_ids: set[str] = set()
    for position, value in enumerate(values, start=1):
        item = value if isinstance(value, dict) else {}
        raw_item_id = item.get("id")
        row_identifier_valid = isinstance(raw_item_id, str) and bool(raw_item_id.strip())
        item_id = raw_item_id.strip() if row_identifier_valid else f"invalid-number-{position}"
        if not row_identifier_valid or item_id in seen_row_ids:
            issues.append("number audit row IDs must be unique, non-empty strings")
            row_identifier_valid = False
        seen_row_ids.add(item_id)
        critical = item_id in critical_fields or bool(item.get("critical", False))
        report = item.get("report") if isinstance(item.get("report"), dict) else {}
        source = item.get("source") if isinstance(item.get("source"), dict) else {}
        source_issues = _source_issues(source.get("source_ids"), known_sources, f"number audit {item_id}")
        issues.extend(source_issues)
        source_ids = _string_ids(source.get("source_ids"))
        groups = sorted(
            {
                str(registry[source_id].get("independence_group"))
                for source_id in source_ids
                if source_id in registry
                and source_id in known_sources
                and registry[source_id].get("independence_group")
            }
        )
        minimum_independence = _positive_integral(
            item.get("minimum_independent_sources", default_minimum_independence)
        )
        row_independence_valid = minimum_independence is not None
        if minimum_independence is None:
            issues.append(
                f"number audit {item_id} minimum_independent_sources must be a positive integer"
            )
            minimum_independence = default_minimum_independence
        report_value = _decimal(report.get("value"))
        source_value = _decimal(source.get("value"))
        report_scale = _decimal(report.get("scale", 1))
        source_scale = _decimal(source.get("scale", 1))
        absolute_tolerance = _decimal((item.get("tolerance") or {}).get("absolute", 0)) if isinstance(item.get("tolerance"), dict) else Decimal("0")
        relative_tolerance = _decimal((item.get("tolerance") or {}).get("relative", 0)) if isinstance(item.get("tolerance"), dict) else Decimal("0")
        mismatches = _metadata_mismatches(report, source)
        missing_metadata = _missing_audit_metadata(report, source)
        row: dict[str, Any] = {
            "id": item_id,
            "label": item.get("label"),
            "critical": critical,
            "report": copy.deepcopy(report),
            "source": copy.deepcopy(source),
            "tolerance": copy.deepcopy(
                item.get("tolerance") if isinstance(item.get("tolerance"), dict) else {}
            ),
            "source_ids": source_ids,
            "independence_groups": groups,
            "independent_source_count": len(groups),
            "minimum_independent_sources": minimum_independence,
            "metadata_mismatches": mismatches,
            "missing_metadata": missing_metadata,
        }
        if (
            report_value is None
            or source_value is None
            or report_scale is None
            or source_scale is None
            or absolute_tolerance is None
            or relative_tolerance is None
            or absolute_tolerance < 0
            or relative_tolerance < 0
            or source_issues
            or missing_metadata
            or not row_identifier_valid
            or not independence_configuration_valid
            or not row_independence_valid
            or len(groups) < minimum_independence
        ):
            row.update(
                {
                    "status": "unverifiable",
                    "reason": "value, scale, tolerance, source lineage or source-independence requirement is invalid",
                }
            )
        else:
            report_normalized = report_value * report_scale
            source_normalized = source_value * source_scale
            difference = abs(report_normalized - source_normalized)
            allowed = max(absolute_tolerance, abs(source_normalized) * relative_tolerance)
            passed = not mismatches and difference <= allowed
            row.update(
                {
                    "status": "pass" if passed else "fail",
                    "report_normalized": _decimal_text(report_normalized),
                    "source_normalized": _decimal_text(source_normalized),
                    "absolute_difference": _decimal_text(difference),
                    "allowed_difference": _decimal_text(allowed),
                    "reason": None if passed else "numeric tolerance or metadata comparison failed",
                }
            )
        rows.append(row)
    counts = {state: sum(1 for row in rows if row["status"] == state) for state in AUDIT_STATES}
    row_ids = {row["id"] for row in rows}
    missing_critical_fields = [field for field in critical_fields if field not in row_ids]
    critical_failures = [row["id"] for row in rows if row["critical"] and row["status"] != "pass"]
    critical_failures.extend(missing_critical_fields)
    verified_count = counts["pass"]
    if required and verified_count == 0:
        critical_failures.append("zero_verified_fields")
    if required and not critical_fields:
        critical_failures.append("critical_scope_not_declared")
    if required and not independence_configuration_valid:
        critical_failures.append("invalid_independence_requirement")
    all_groups = sorted({group for row in rows for group in row["independence_groups"]})
    critical_failures = list(dict.fromkeys(critical_failures))
    return (
        {
            "required": required,
            "critical_fields": critical_fields,
            "minimum_independent_sources": default_minimum_independence,
            "rows": rows,
            "counts": counts,
            "verified_count": verified_count,
            "missing_critical_fields": missing_critical_fields,
            "critical_failures": critical_failures,
            "independence_groups": all_groups,
            "independent_source_count": len(all_groups),
            "arithmetic": "decimal",
        },
        issues,
    )


def build_review(raw: dict[str, Any]) -> dict[str, Any]:
    """Build researchability, management, thesis-drift and number-audit controls."""
    if not isinstance(raw, dict):
        raise ValueError("Input must be a JSON object")
    sources = copy.deepcopy(raw.get("sources") if isinstance(raw.get("sources"), list) else [])
    known_sources, issues = _known_sources(sources)
    source_registry = {
        str(item.get("id")): item
        for item in sources
        if isinstance(item, dict)
        and isinstance(item.get("id"), str)
        and item.get("id")
    }
    claims, claim_issues = _build_claims(raw.get("claims"), known_sources)
    issues.extend(claim_issues)
    missing: list[str] = []
    if not _valid_offset_timestamp(raw.get("as_of")):
        missing.append("as_of with timezone offset")
    if not sources:
        missing.append("sources")
    if not claims:
        missing.append("claims")
    entity = copy.deepcopy(raw.get("entity") if isinstance(raw.get("entity"), dict) else {})
    if not entity.get("name") and not entity.get("primary_symbol"):
        missing.append("entity name or primary_symbol")

    researchability, researchability_issues = assess_researchability(
        raw.get("researchability"), known_sources
    )
    issues.extend(researchability_issues)
    management_ledger, promise_issues = build_management_ledger(
        raw.get("management_promises"), known_sources, _as_of_date(raw.get("as_of"))
    )
    issues.extend(promise_issues)
    thesis_drift = classify_thesis_drift(raw.get("thesis_comparison"), known_sources)
    issues.extend(thesis_drift["validation_issues"])
    if thesis_drift["comparison_status"] == "limited_no_baseline":
        issues.append("thesis drift is limited because no prior baseline was supplied")
    number_audit, audit_issues = audit_numbers(
        raw.get("number_audit"), known_sources, source_registry
    )
    issues.extend(audit_issues)
    if not number_audit["required"]:
        publication_gate = "not_run"
    elif not number_audit["rows"] or number_audit["critical_failures"]:
        publication_gate = "blocked"
    else:
        publication_gate = "pass"

    issues = list(dict.fromkeys(issues))
    missing = list(dict.fromkeys(missing))
    status = (
        "blocked"
        if missing or publication_gate == "blocked"
        else "limited"
        if issues or researchability["grade"] == "C"
        else "ready"
    )
    return {
        "schema": SCHEMA,
        "schemaVersion": 1,
        "as_of": raw.get("as_of"),
        "entity": entity,
        "sources": sources,
        "claims": claims,
        "researchability": researchability,
        "management_ledger": management_ledger,
        "thesis_drift": thesis_drift,
        "number_audit": number_audit,
        "publication_gate": publication_gate,
        "quality": {
            "status": status,
            "missing": missing,
            "issues": issues,
            "checks": [
                "evidence-lane coverage",
                "management promise deadlines and measurements",
                "fact versus price versus wording drift",
                "critical-number decimal comparison",
                "currency, period and basis alignment",
            ],
        },
    }


def validate_review(review: dict[str, Any]) -> list[str]:
    """Return structural contract violations for an already-built review."""
    errors: list[str] = []
    if not isinstance(review, dict):
        return ["root must be an object"]
    if review.get("schema") != SCHEMA or review.get("schemaVersion") != 1:
        errors.append("schema must be research_review/v1 with schemaVersion 1")
    if not _valid_offset_timestamp(review.get("as_of")):
        errors.append("as_of must be an ISO 8601 timestamp with a timezone offset")
    if not isinstance(review.get("sources"), list) or not review.get("sources"):
        errors.append("sources must be a non-empty array")
    if not isinstance(review.get("claims"), list) or not review.get("claims"):
        errors.append("claims must be a non-empty array")
    for source in review.get("sources") or []:
        if not isinstance(source, dict) or not all(
            source.get(field) for field in ("id", "origin", "independence_group")
        ):
            errors.append("every source requires id, origin and independence_group")
    for claim in review.get("claims") or []:
        if (
            not isinstance(claim, dict)
            or not isinstance(claim.get("id"), str)
            or not claim.get("id")
            or not isinstance(claim.get("statement"), str)
            or not claim.get("statement")
            or not isinstance(claim.get("source_ids"), list)
            or not claim.get("source_ids")
        ):
            errors.append("every claim requires id, statement and source_ids")
    source_list = review.get("sources") if isinstance(review.get("sources"), list) else []
    known_sources, source_issues = _known_sources(source_list)
    errors.extend(f"source registry: {issue}" for issue in source_issues)
    _, claim_issues = _build_claims(review.get("claims"), known_sources)
    errors.extend(f"claim registry: {issue}" for issue in claim_issues)
    researchability = review.get("researchability") if isinstance(review.get("researchability"), dict) else {}
    if researchability.get("grade") not in {"A", "B", "C"}:
        errors.append("researchability.grade must be A, B or C")
    if researchability.get("maximum_supported_confidence") not in {"high", "medium", "low"}:
        errors.append("researchability.maximum_supported_confidence is invalid")
    drift = review.get("thesis_drift") if isinstance(review.get("thesis_drift"), dict) else {}
    if drift.get("comparison_status") not in {"complete", "limited_no_baseline"}:
        errors.append("thesis_drift.comparison_status is invalid")
    if drift.get("substantive_state") not in {"facts_changed", "valuation_changed", "unchanged"}:
        errors.append("thesis_drift.substantive_state is invalid")
    if review.get("publication_gate") not in {"pass", "blocked", "not_run"}:
        errors.append("publication_gate must be pass, blocked or not_run")
    quality = review.get("quality") if isinstance(review.get("quality"), dict) else {}
    if quality.get("status") not in {"ready", "limited", "blocked"}:
        errors.append("quality.status must be ready, limited or blocked")
    if drift.get("comparison_status") == "limited_no_baseline" and quality.get("status") == "ready":
        errors.append("a review without a thesis baseline cannot have ready quality")
    if review.get("publication_gate") == "blocked" and quality.get("status") != "blocked":
        errors.append("a blocked publication gate requires quality.status blocked")
    number_audit = review.get("number_audit") if isinstance(review.get("number_audit"), dict) else {}
    if number_audit.get("required") and (
        not number_audit.get("critical_fields")
        or not number_audit.get("verified_count")
        or number_audit.get("critical_failures")
    ) and review.get("publication_gate") != "blocked":
        errors.append("an incomplete required number audit must block publication")
    for item in review.get("management_ledger") or []:
        if not isinstance(item, dict) or item.get("status") not in PROMISE_STATES:
            errors.append("management ledger contains an invalid promise status")
    ledger_input = review.get("management_ledger") if isinstance(review.get("management_ledger"), list) else []
    expected_ledger, ledger_issues = build_management_ledger(
        ledger_input, known_sources, _as_of_date(review.get("as_of"))
    )
    errors.extend(f"management ledger: {issue}" for issue in ledger_issues)
    if len(ledger_input) == len(expected_ledger):
        for original, expected in zip(ledger_input, expected_ledger):
            if not isinstance(original, dict):
                continue
            for field in ("status", "determination"):
                if original.get(field) != expected.get(field):
                    errors.append(
                        f"management promise {original.get('id')} has inconsistent derived field {field}"
                    )
    for row in (review.get("number_audit") or {}).get("rows", []):
        if not isinstance(row, dict) or row.get("status") not in AUDIT_STATES:
            errors.append("number audit contains an invalid row status")
    expected_researchability, researchability_issues = assess_researchability(
        researchability, known_sources
    )
    errors.extend(f"researchability: {issue}" for issue in researchability_issues)
    for field in ("grade", "maximum_supported_confidence", "coverage", "required_missing"):
        if researchability.get(field) != expected_researchability.get(field):
            errors.append(f"researchability.{field} does not match recomputed evidence coverage")

    changes = drift.get("changes") if isinstance(drift.get("changes"), list) else []
    change_classes = {
        item.get("classification")
        for item in changes
        if isinstance(item, dict) and item.get("classification") in DRIFT_CLASSES
    }
    expected_primary = next((name for name in DRIFT_CLASSES if name in change_classes), "no_change")
    expected_substantive = (
        "facts_changed"
        if "fact" in change_classes
        else "valuation_changed"
        if "price" in change_classes
        else "unchanged"
    )
    if drift.get("primary_class") != expected_primary:
        errors.append("thesis_drift.primary_class does not match its changes")
    if drift.get("substantive_state") != expected_substantive:
        errors.append("thesis_drift.substantive_state does not match its changes")
    expected_drift_issues: list[str] = []
    for change in changes:
        if not isinstance(change, dict) or change.get("classification") != "fact":
            continue
        after = change.get("after")
        source_ids = after.get("source_ids") if isinstance(after, dict) else None
        expected_drift_issues.extend(
            _source_issues(
                source_ids,
                known_sources,
                f"changed thesis fact {change.get('path')}",
                required=True,
            )
        )
    effect = drift.get("effect_on_conclusion") if isinstance(
        drift.get("effect_on_conclusion"), dict
    ) else {}
    if effect.get("direction") not in CONCLUSION_EFFECTS:
        expected_drift_issues.append("effect_on_conclusion.direction is invalid")
    if expected_substantive != "unchanged":
        if not effect.get("rationale"):
            expected_drift_issues.append(
                "effect_on_conclusion requires rationale for a substantive change"
            )
        expected_drift_issues.extend(
            _source_issues(
                effect.get("source_ids"),
                known_sources,
                "effect_on_conclusion",
                required=True,
            )
        )
    if drift.get("validation_issues") != expected_drift_issues:
        errors.append("thesis_drift.validation_issues does not match sourced changes and conclusion effect")

    source_registry = {
        str(item.get("id")): item
        for item in source_list
        if isinstance(item, dict)
        and isinstance(item.get("id"), str)
        and item.get("id")
    }
    audit_rows = []
    for row in number_audit.get("rows") or []:
        if not isinstance(row, dict):
            continue
        audit_rows.append(
            {
                "id": row.get("id"),
                "label": row.get("label"),
                "critical": row.get("critical", False),
                "report": copy.deepcopy(row.get("report") or {}),
                "source": copy.deepcopy(row.get("source") or {}),
                "tolerance": copy.deepcopy(row.get("tolerance") or {}),
                "minimum_independent_sources": row.get(
                    "minimum_independent_sources",
                    number_audit.get("minimum_independent_sources", 1),
                ),
            }
        )
    recomputed_audit, recomputed_issues = audit_numbers(
        {
            "required": bool(number_audit.get("required")),
            "critical_fields": list(number_audit.get("critical_fields") or []),
            "minimum_independent_sources": number_audit.get(
                "minimum_independent_sources", 1
            ),
            "rows": audit_rows,
        },
        known_sources,
        source_registry,
    )
    errors.extend(f"number audit: {issue}" for issue in recomputed_issues)
    for field in (
        "counts",
        "verified_count",
        "missing_critical_fields",
        "critical_failures",
        "independence_groups",
        "independent_source_count",
    ):
        if number_audit.get(field) != recomputed_audit.get(field):
            errors.append(f"number_audit.{field} does not match recomputed verification")
    original_rows = number_audit.get("rows") or []
    expected_rows = recomputed_audit.get("rows") or []
    if len(original_rows) == len(expected_rows):
        for original, expected in zip(original_rows, expected_rows):
            if not isinstance(original, dict):
                continue
            for field in (
                "status",
                "independence_groups",
                "independent_source_count",
                "metadata_mismatches",
                "missing_metadata",
                "report_normalized",
                "source_normalized",
                "absolute_difference",
                "allowed_difference",
            ):
                if original.get(field) != expected.get(field):
                    errors.append(
                        f"number audit row {original.get('id')} has inconsistent derived field {field}"
                    )
    expected_gate = (
        "not_run"
        if not recomputed_audit["required"]
        else "blocked"
        if not recomputed_audit["rows"] or recomputed_audit["critical_failures"]
        else "pass"
    )
    if review.get("publication_gate") != expected_gate:
        errors.append("publication_gate does not match recomputed number-audit readiness")
    return errors


def strict_ready(review: dict[str, Any], errors: list[str] | None = None) -> bool:
    return (
        isinstance(review, dict)
        and not errors
        and (review.get("quality") or {}).get("status") == "ready"
        and review.get("publication_gate") == "pass"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--validate-only", action="store_true")
    parser.add_argument("--strict", action="store_true", help="Exit 2 unless quality and publication gate pass")
    args = parser.parse_args()
    try:
        raw = json.loads(args.input.read_text(encoding="utf-8"), parse_float=Decimal)
        if args.validate_only:
            errors = validate_review(raw)
            result: dict[str, Any] = {"valid": not errors, "errors": errors}
        else:
            result = build_review(raw)
            errors = validate_review(result)
            if errors:
                raise ValueError("; ".join(errors))
        rendered = json.dumps(
            result,
            indent=2,
            ensure_ascii=False,
            allow_nan=False,
            default=_json_default,
        ) + "\n"
    except (OSError, json.JSONDecodeError, TypeError, ValueError) as exc:
        raise SystemExit(str(exc)) from exc
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    if args.strict:
        checked_review = raw if args.validate_only else result
        if not strict_ready(checked_review, errors):
            raise SystemExit(2)


if __name__ == "__main__":
    main()
