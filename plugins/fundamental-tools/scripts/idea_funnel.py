"""Build and validate the dependency-free ``idea_funnel/v1`` contract."""

from __future__ import annotations

import argparse
import copy
import json
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any


SCHEMA = "idea_funnel/v1"
CAUSAL_STATUSES = {"supported", "disputed", "unsupported", "unknown"}
DISPOSITIONS = {"advance", "watch", "reject"}
SCORE_DIMENSIONS = (
    "exposure_purity",
    "bottleneck_leverage",
    "fundamental_quality",
    "expectations_gap",
    "valuation_asymmetry",
    "catalyst_credibility",
    "falsifier_resilience",
)
BOTTLENECK_DIMENSIONS = (
    "supplier_concentration",
    "capacity_tightness",
    "expansion_lead_time",
    "qualification_friction",
    "substitution_difficulty",
    "demand_capacity_gap",
)
EVIDENCE_LANES = (
    "exposure",
    "fundamentals",
    "expectations",
    "valuation",
    "catalysts",
    "falsifiers",
)
SCREEN_STATES = {"pass", "fail", "insufficient", "not_applicable"}
SCREEN_OPERATORS = {"gt", "gte", "lt", "lte", "eq", "between"}


def _decimal(value: Any) -> Decimal | None:
    """Parse a finite decimal without binary floating-point arithmetic."""
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


def _rounded(value: Decimal | None, places: str = "0.0001") -> str | None:
    if value is None:
        return None
    rendered = format(value.quantize(Decimal(places)), "f")
    return rendered.rstrip("0").rstrip(".") or "0"


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


def _known_sources(sources: list[dict[str, Any]]) -> tuple[set[str], list[str]]:
    ids = [item.get("id") for item in sources if isinstance(item, dict)]
    valid_ids = [item for item in ids if isinstance(item, str) and item.strip()]
    valid: set[str] = set()
    issues: list[str] = []
    if len(ids) != len(valid_ids) or len(valid_ids) != len(set(valid_ids)):
        issues.append("source IDs must be unique, non-empty strings")
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
            valid.add(source_id)
    return valid, issues


def _build_claims(
    raw: Any,
    known_sources: set[str],
) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]], list[str]]:
    claims = copy.deepcopy(raw if isinstance(raw, list) else [])
    registry: dict[str, dict[str, Any]] = {}
    issues: list[str] = []
    raw_ids = [
        value.get("id").strip()
        for value in claims
        if isinstance(value, dict)
        and isinstance(value.get("id"), str)
        and value.get("id").strip()
    ]
    duplicate_ids = {claim_id for claim_id in raw_ids if raw_ids.count(claim_id) > 1}
    if duplicate_ids:
        issues.append("claim IDs must be unique, non-empty strings")
    for position, value in enumerate(claims, start=1):
        if not isinstance(value, dict):
            issues.append(f"claim {position} must be an object")
            continue
        raw_claim_id = value.get("id")
        claim_id = raw_claim_id.strip() if isinstance(raw_claim_id, str) else ""
        if not claim_id:
            issues.append("claim IDs must be unique, non-empty strings")
            continue
        if not value.get("statement"):
            issues.append(f"claim {claim_id} requires a statement")
        claim_issues = _source_issues(value.get("source_ids"), known_sources, f"claim {claim_id}")
        issues.extend(claim_issues)
        if claim_id not in duplicate_ids and value.get("statement") and not claim_issues:
            registry[claim_id] = value
    return claims, registry, issues


def _source_issues(
    source_ids: Any,
    known: set[str],
    location: str,
    *,
    required: bool = True,
) -> list[str]:
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


def _lineage_issues(
    item: dict[str, Any],
    known_sources: set[str],
    claims: dict[str, dict[str, Any]],
    location: str,
) -> list[str]:
    source_ids = item.get("source_ids") if isinstance(item.get("source_ids"), list) else []
    claim_ids = item.get("claim_ids") if isinstance(item.get("claim_ids"), list) else []
    issues: list[str] = []
    invalid_claims = [
        claim_id for claim_id in claim_ids if not isinstance(claim_id, str) or not claim_id.strip()
    ]
    if invalid_claims:
        issues.append(f"{location} claim_ids must contain only non-empty strings")
    unknown_claims = {
        claim_id for claim_id in claim_ids if isinstance(claim_id, str) and claim_id not in claims
    }
    if unknown_claims:
        issues.append(f"{location} references unknown claim IDs: {', '.join(sorted(map(str, unknown_claims)))}")
    if not source_ids and not claim_ids:
        issues.append(f"{location} requires source_ids or claim_ids")
    issues.extend(_source_issues(source_ids, known_sources, location, required=False))
    return issues


def _score_item(
    value: Any,
    known_sources: set[str],
    claims: dict[str, dict[str, Any]],
    location: str,
) -> tuple[dict[str, Any], list[str]]:
    item = copy.deepcopy(value) if isinstance(value, dict) else {"score": value}
    score = _decimal(item.get("score"))
    issues: list[str] = []
    if score is None or score < 0 or score > 5:
        issues.append(f"{location}.score must be between 0 and 5")
        normalized = None
    else:
        normalized = _rounded(score)
    issues.extend(_lineage_issues(item, known_sources, claims, location))
    item["score"] = normalized
    return item, issues


def _weighted_score(
    values: dict[str, Decimal],
    weights: dict[str, Decimal],
) -> Decimal | None:
    denominator = sum((weights[key] for key in values), Decimal("0"))
    if denominator <= 0:
        return None
    weighted = sum((values[key] * weights[key] for key in values), Decimal("0"))
    return weighted / denominator * Decimal("20")


def _weights(raw: Any, dimensions: tuple[str, ...], location: str) -> tuple[dict[str, Decimal], list[str]]:
    supplied = raw if isinstance(raw, dict) else {}
    output: dict[str, Decimal] = {}
    issues: list[str] = []
    for dimension in dimensions:
        value = _decimal(supplied.get(dimension, 1))
        if value is None or value < 0:
            issues.append(f"{location}.{dimension} must be a non-negative number")
            value = Decimal("1")
        output[dimension] = value
    if sum(output.values(), Decimal("0")) <= 0:
        issues.append(f"{location} must contain at least one positive weight")
        output = {dimension: Decimal("1") for dimension in dimensions}
    return output, issues


def evaluate_screen(profile: dict[str, Any], inputs: dict[str, Any]) -> dict[str, Any]:
    """Evaluate an explicit sector/profile rule set without implicit cutoffs."""
    results: list[dict[str, Any]] = []
    configuration_errors: list[str] = []
    rules = profile.get("rules") if isinstance(profile.get("rules"), list) else []
    if not rules:
        configuration_errors.append("profile requires at least one rule")
    for position, raw_rule in enumerate(rules, start=1):
        rule = raw_rule if isinstance(raw_rule, dict) else {}
        rule_id = str(rule.get("id") or f"rule-{position}")
        metric = str(rule.get("metric") or "")
        operator = str(rule.get("operator") or "")
        required = bool(rule.get("required", True))
        supplied = inputs.get(metric)
        input_item = supplied if isinstance(supplied, dict) else {"value": supplied}
        input_state = str(input_item.get("state") or "available")
        result: dict[str, Any] = {
            "rule_id": rule_id,
            "metric": metric,
            "required": required,
            "operator": operator,
        }
        if not metric:
            configuration_errors.append(f"{rule_id}: metric is required")
            result.update({"state": "insufficient", "reason": "rule has no metric"})
            results.append(result)
            continue
        if operator not in SCREEN_OPERATORS:
            configuration_errors.append(f"{rule_id}: unsupported operator {operator!r}")
            result.update({"state": "insufficient", "reason": "rule operator is invalid"})
            results.append(result)
            continue
        if input_state not in {"available", "not_applicable", "insufficient"}:
            configuration_errors.append(f"{rule_id}: invalid input state {input_state!r}")
            result.update({"state": "insufficient", "reason": "input state is invalid"})
            results.append(result)
            continue
        if input_state in {"not_applicable", "insufficient"}:
            result.update(
                {
                    "state": input_state,
                    "reason": input_item.get("reason") or f"input marked {input_state}",
                }
            )
            results.append(result)
            continue
        value = _decimal(input_item.get("value"))
        if value is None:
            result.update({"state": "insufficient", "reason": "numeric input is unavailable"})
            results.append(result)
            continue

        threshold = _decimal(rule.get("threshold"))
        lower = _decimal(rule.get("lower"))
        upper = _decimal(rule.get("upper"))
        if operator == "between":
            configured = lower is not None and upper is not None and lower <= upper
            passed = bool(configured and lower <= value <= upper)
            rendered_threshold: Any = {
                "lower": None if lower is None else str(lower),
                "upper": None if upper is None else str(upper),
            }
        else:
            configured = threshold is not None
            comparisons = {
                "gt": lambda: value > threshold,
                "gte": lambda: value >= threshold,
                "lt": lambda: value < threshold,
                "lte": lambda: value <= threshold,
                "eq": lambda: value == threshold,
            }
            passed = bool(configured and comparisons[operator]())
            rendered_threshold = None if threshold is None else str(threshold)
        if not configured:
            configuration_errors.append(f"{rule_id}: explicit threshold is required")
            result.update({"state": "insufficient", "reason": "rule threshold is unavailable"})
        else:
            result.update(
                {
                    "state": "pass" if passed else "fail",
                    "value": str(value),
                    "threshold": rendered_threshold,
                }
            )
        results.append(result)

    required_results = [item for item in results if item["required"]]
    applicable_required = [item for item in required_results if item["state"] != "not_applicable"]
    if configuration_errors or any(item["state"] == "insufficient" for item in applicable_required):
        overall = "insufficient"
    elif any(item["state"] == "fail" for item in applicable_required):
        overall = "fail"
    elif not applicable_required:
        overall = "not_applicable"
    else:
        overall = "pass"
    return {
        "profile_id": profile.get("id"),
        "profile_kind": profile.get("kind", "sector-quality"),
        "state": overall,
        "results": results,
        "configuration_errors": configuration_errors,
    }


def _build_bottlenecks(
    raw: Any,
    known_sources: set[str],
    claims: dict[str, dict[str, Any]],
    weights: dict[str, Decimal],
) -> tuple[list[dict[str, Any]], list[str]]:
    output: list[dict[str, Any]] = []
    issues: list[str] = []
    for position, value in enumerate(raw if isinstance(raw, list) else [], start=1):
        item = copy.deepcopy(value) if isinstance(value, dict) else {}
        item_id = str(item.get("id") or f"bottleneck-{position}")
        item["id"] = item_id
        dimensions = item.get("dimensions") if isinstance(item.get("dimensions"), dict) else {}
        normalized: dict[str, Any] = {}
        numeric: dict[str, Decimal] = {}
        lineage_valid = True
        for dimension in BOTTLENECK_DIMENSIONS:
            score_item, score_issues = _score_item(
                dimensions.get(dimension), known_sources, claims, f"bottleneck {item_id}.{dimension}"
            )
            normalized[dimension] = score_item
            score = _decimal(score_item.get("score"))
            if score is not None:
                numeric[dimension] = score
            issues.extend(score_issues)
            if score_issues:
                lineage_valid = False
        item["dimensions"] = normalized
        complete = len(numeric) == len(BOTTLENECK_DIMENSIONS) and lineage_valid
        item["score"] = _rounded(_weighted_score(numeric, weights)) if complete else None
        item["score_complete"] = complete
        item["score_lineage_valid"] = lineage_valid
        issues.extend(_lineage_issues(item, known_sources, claims, f"bottleneck {item_id}"))
        output.append(item)
    return output, issues


def _evidence_coverage(
    evidence: dict[str, Any],
    known_sources: set[str],
    claims: dict[str, dict[str, Any]],
    candidate_id: str,
) -> tuple[str, list[str]]:
    covered = 0
    issues: list[str] = []
    for lane in EVIDENCE_LANES:
        items = evidence.get(lane) if isinstance(evidence.get(lane), list) else []
        valid_items = 0
        if not items:
            issues.append(f"candidate {candidate_id} requires {lane} evidence")
        for position, value in enumerate(items, start=1):
            item = value if isinstance(value, dict) else {}
            item_issues = _lineage_issues(
                item, known_sources, claims, f"candidate {candidate_id}.{lane}[{position}]"
            )
            issues.extend(item_issues)
            if item.get("claim") and not item_issues:
                valid_items += 1
        if valid_items:
            covered += 1
    coverage = Decimal(covered) / Decimal(len(EVIDENCE_LANES))
    return _rounded(coverage) or "0", issues


def build_funnel(raw: dict[str, Any]) -> dict[str, Any]:
    """Normalize inputs, calculate screens/scores, and rank eligible candidates."""
    if not isinstance(raw, dict):
        raise ValueError("Input must be a JSON object")
    sources = copy.deepcopy(raw.get("sources") if isinstance(raw.get("sources"), list) else [])
    known_sources, issues = _known_sources(sources)
    claims, claim_registry, claim_issues = _build_claims(raw.get("claims"), known_sources)
    issues.extend(claim_issues)
    warnings: list[str] = []
    foundational_missing: list[str] = []
    if not _valid_offset_timestamp(raw.get("as_of")):
        foundational_missing.append("as_of with timezone offset")
    if not str(raw.get("question") or "").strip():
        foundational_missing.append("question")
    scope = copy.deepcopy(raw.get("scope") if isinstance(raw.get("scope"), dict) else {})
    if not scope:
        foundational_missing.append("scope")
    if not sources:
        foundational_missing.append("sources")
    if not claims:
        foundational_missing.append("claims")

    causal_chain: list[dict[str, Any]] = []
    for position, value in enumerate(raw.get("causal_chain") or [], start=1):
        item = copy.deepcopy(value) if isinstance(value, dict) else {}
        item["id"] = str(item.get("id") or f"link-{position}")
        status = str(item.get("status") or "unknown")
        if status not in CAUSAL_STATUSES:
            issues.append(f"causal link {item['id']} has invalid status {status!r}")
            status = "unknown"
        item["status"] = status
        item["required"] = bool(item.get("required", True))
        fields_complete = bool(item.get("from") and item.get("to") and item.get("mechanism"))
        if not fields_complete:
            issues.append(f"causal link {item['id']} requires from, to and mechanism")
        lineage_issues = _lineage_issues(
            item, known_sources, claim_registry, f"causal link {item['id']}"
        )
        issues.extend(lineage_issues)
        item["lineage_valid"] = fields_complete and not lineage_issues
        causal_chain.append(item)
    if not causal_chain:
        foundational_missing.append("causal_chain")
    blocking_links = [
        item["id"]
        for item in causal_chain
        if item.get("required", True)
        and (item.get("status") != "supported" or not item.get("lineage_valid"))
    ]
    causal_gate = {
        "state": "blocked" if blocking_links else "pass",
        "blocking_link_ids": blocking_links,
        "rule": "Every required causal link must be supported before candidates can rank.",
    }

    bottleneck_weight_input = (raw.get("bottleneck_scoring") or {}).get("weights") if isinstance(raw.get("bottleneck_scoring"), dict) else {}
    bottleneck_weights, weight_issues = _weights(
        bottleneck_weight_input, BOTTLENECK_DIMENSIONS, "bottleneck_scoring.weights"
    )
    issues.extend(weight_issues)
    bottlenecks, bottleneck_issues = _build_bottlenecks(
        raw.get("bottlenecks"), known_sources, claim_registry, bottleneck_weights
    )
    issues.extend(bottleneck_issues)
    if not bottlenecks:
        warnings.append("no bottleneck or constraint record was supplied")

    profiles = copy.deepcopy(raw.get("screen_profiles") if isinstance(raw.get("screen_profiles"), list) else [])
    profiles_by_id = {
        str(item.get("id")): item
        for item in profiles
        if isinstance(item, dict) and item.get("id")
    }
    if len(profiles_by_id) != len(profiles):
        issues.append("screen profile IDs must be unique, non-empty strings")

    ranking_input = raw.get("ranking_method") if isinstance(raw.get("ranking_method"), dict) else {}
    candidate_weights, candidate_weight_issues = _weights(
        ranking_input.get("weights"), SCORE_DIMENSIONS, "ranking_method.weights"
    )
    issues.extend(candidate_weight_issues)
    candidates: list[dict[str, Any]] = []
    for position, value in enumerate(raw.get("candidates") or [], start=1):
        candidate = copy.deepcopy(value) if isinstance(value, dict) else {}
        candidate_id = str(candidate.get("id") or f"candidate-{position}")
        candidate["id"] = candidate_id
        entity = candidate.get("entity") if isinstance(candidate.get("entity"), dict) else {}
        identity_complete = all(entity.get(field) for field in ("name", "primary_symbol", "exchange"))
        if not identity_complete:
            issues.append(
                f"candidate {candidate_id} requires entity.name, entity.primary_symbol and entity.exchange"
            )
        chain_role_complete = bool(candidate.get("supply_chain_position"))
        if not chain_role_complete:
            issues.append(f"candidate {candidate_id} requires supply_chain_position")
        exposure = candidate.get("exposure") if isinstance(candidate.get("exposure"), dict) else {}
        exposure_complete = bool(exposure.get("description"))
        exposure_lineage_valid = False
        if not exposure_complete:
            issues.append(f"candidate {candidate_id} requires an exposure description")
        else:
            exposure_issues = _lineage_issues(
                exposure,
                known_sources,
                claim_registry,
                f"candidate {candidate_id}.exposure",
            )
            issues.extend(exposure_issues)
            exposure_lineage_valid = not exposure_issues
        candidate["exposure"] = exposure
        candidate["exposure_lineage_valid"] = exposure_lineage_valid
        disposition = str(candidate.get("disposition") or "watch")
        if disposition not in DISPOSITIONS:
            issues.append(f"candidate {candidate_id} has invalid disposition {disposition!r}")
            disposition = "watch"
        candidate["disposition"] = disposition
        rejection_reasons = candidate.get("rejection_reasons") if isinstance(candidate.get("rejection_reasons"), list) else []
        candidate["rejection_reasons"] = rejection_reasons
        if disposition == "reject" and not rejection_reasons:
            issues.append(f"rejected candidate {candidate_id} requires an explicit rejection reason")

        evidence = candidate.get("evidence") if isinstance(candidate.get("evidence"), dict) else {}
        coverage, evidence_issues = _evidence_coverage(
            evidence, known_sources, claim_registry, candidate_id
        )
        if disposition != "reject":
            issues.extend(evidence_issues)
        candidate["evidence"] = evidence
        candidate["evidence_coverage"] = coverage

        normalized_scores: dict[str, Any] = {}
        numeric_scores: dict[str, Decimal] = {}
        score_lineage_valid = True
        raw_scores = candidate.get("scores") if isinstance(candidate.get("scores"), dict) else {}
        for dimension in SCORE_DIMENSIONS:
            score_item, score_issues = _score_item(
                raw_scores.get(dimension),
                known_sources,
                claim_registry,
                f"candidate {candidate_id}.scores.{dimension}",
            )
            normalized_scores[dimension] = score_item
            score = _decimal(score_item.get("score"))
            if score is not None:
                numeric_scores[dimension] = score
            if disposition != "reject":
                issues.extend(score_issues)
                if score_issues:
                    score_lineage_valid = False
        candidate["scores"] = normalized_scores
        candidate["score_lineage_valid"] = score_lineage_valid

        screen_state = "not_applicable"
        profile_id = candidate.get("screen_profile_id")
        profile_key = str(profile_id) if profile_id is not None else ""
        profile_found = False
        if profile_id:
            profile = profiles_by_id.get(profile_key)
            if profile is None:
                issues.append(f"candidate {candidate_id} references unknown screen profile {profile_id!r}")
                candidate["screen"] = {
                    "profile_id": profile_id,
                    "state": "insufficient",
                    "results": [],
                    "configuration_errors": ["profile not found"],
                }
            else:
                profile_found = True
                inputs = candidate.get("screen_inputs") if isinstance(candidate.get("screen_inputs"), dict) else {}
                candidate["screen"] = evaluate_screen(profile, inputs)
            screen_state = candidate["screen"]["state"]
            if candidate["screen"].get("configuration_errors"):
                issues.extend(
                    f"candidate {candidate_id} screen: {message}"
                    for message in candidate["screen"]["configuration_errors"]
                )

        scores_complete = (
            len(numeric_scores) == len(SCORE_DIMENSIONS) and score_lineage_valid
        )
        ranking_score = _weighted_score(numeric_scores, candidate_weights) if scores_complete else None
        rankability_reasons: list[str] = []
        if disposition == "reject":
            rankability_reasons.append("research disposition is reject")
        if Decimal(coverage) != Decimal("1"):
            rankability_reasons.append("evidence lanes are incomplete")
        if not scores_complete:
            rankability_reasons.append("ranking scores or their lineage are incomplete")
        screen_gate_pass = bool(profile_id and profile_found and screen_state == "pass")
        if not screen_gate_pass:
            rankability_reasons.append(
                "a declared, found screen profile with applicable required rules must pass"
            )
        if causal_gate["state"] != "pass":
            rankability_reasons.append("one or more required causal links are not supported")
        if not identity_complete:
            rankability_reasons.append("listing identity is incomplete")
        if not chain_role_complete:
            rankability_reasons.append("supply-chain position is missing")
        if not exposure_complete:
            rankability_reasons.append("exposure description is missing")
        elif not exposure_lineage_valid:
            rankability_reasons.append("exposure lineage is invalid")
        rankable = (
            disposition != "reject"
            and Decimal(coverage) == Decimal("1")
            and scores_complete
            and screen_gate_pass
            and causal_gate["state"] == "pass"
            and identity_complete
            and chain_role_complete
            and exposure_complete
            and exposure_lineage_valid
        )
        candidate["ranking_score"] = _rounded(ranking_score) if rankable else None
        candidate["rankable"] = rankable
        candidate["rankability_reasons"] = rankability_reasons
        if disposition != "reject" and not rankable:
            warnings.append(f"candidate {candidate_id} is excluded from ranking until evidence, scores and required screen rules are complete")
        candidates.append(candidate)
    if not candidates:
        foundational_missing.append("candidates")

    ranked = sorted(
        (item for item in candidates if item["rankable"]),
        key=lambda item: (-Decimal(item["ranking_score"]), item["id"]),
    )
    ranking = [
        {
            "rank": position,
            "candidate_id": item["id"],
            "score": item["ranking_score"],
            "evidence_coverage": item["evidence_coverage"],
        }
        for position, item in enumerate(ranked, start=1)
    ]
    if candidates and not ranking:
        warnings.append("no candidate currently meets the evidence and screen gates for ranking")

    issues = list(dict.fromkeys(issues))
    warnings = list(dict.fromkeys(warnings))
    foundational_missing = list(dict.fromkeys(foundational_missing))
    status = "blocked" if foundational_missing else "limited" if issues or warnings else "ready"
    return {
        "schema": SCHEMA,
        "schemaVersion": 1,
        "as_of": raw.get("as_of"),
        "question": raw.get("question"),
        "scope": scope,
        "sources": sources,
        "claims": claims,
        "causal_chain": causal_chain,
        "causal_gate": causal_gate,
        "bottlenecks": bottlenecks,
        "bottleneck_scoring": {
            "scale": "0-100",
            "weights": {key: _rounded(value) for key, value in bottleneck_weights.items()},
            "note": "Weights rank constraints; they are not sector quality thresholds.",
        },
        "screen_profiles": profiles,
        "candidates": candidates,
        "ranking_method": {
            "scale": "0-100",
            "weights": {key: _rounded(value) for key, value in candidate_weights.items()},
            "note": "Scores and weights are explicit research inputs, not investment recommendations.",
        },
        "ranking": ranking,
        "quality": {
            "status": status,
            "missing": foundational_missing,
            "issues": issues,
            "warnings": warnings,
            "checks": [
                "source IDs and timezone",
                "causal-chain support",
                "bottleneck evidence and scoring completeness",
                "candidate evidence-lane coverage",
                "explicit sector/profile screen thresholds",
                "rejected-candidate reasons",
                "ranking score completeness",
            ],
        },
    }


def validate_funnel(pack: dict[str, Any]) -> list[str]:
    """Return structural contract violations for an already-built funnel."""
    errors: list[str] = []
    if not isinstance(pack, dict):
        return ["root must be an object"]
    if pack.get("schema") != SCHEMA or pack.get("schemaVersion") != 1:
        errors.append("schema must be idea_funnel/v1 with schemaVersion 1")
    if not _valid_offset_timestamp(pack.get("as_of")):
        errors.append("as_of must be an ISO 8601 timestamp with a timezone offset")
    for field in ("sources", "claims", "causal_chain", "candidates", "ranking"):
        if not isinstance(pack.get(field), list):
            errors.append(f"{field} must be an array")
    for field in ("sources", "claims", "causal_chain", "candidates"):
        if isinstance(pack.get(field), list) and not pack.get(field):
            errors.append(f"{field} must not be empty")
    for source in pack.get("sources") or []:
        if not isinstance(source, dict) or not all(
            source.get(field) for field in ("id", "origin", "independence_group")
        ):
            errors.append("every source requires id, origin and independence_group")
    for claim in pack.get("claims") or []:
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
    causal_gate = pack.get("causal_gate") if isinstance(pack.get("causal_gate"), dict) else {}
    if causal_gate.get("state") not in {"pass", "blocked"}:
        errors.append("causal_gate.state must be pass or blocked")
    quality = pack.get("quality") if isinstance(pack.get("quality"), dict) else {}
    if quality.get("status") not in {"ready", "limited", "blocked"}:
        errors.append("quality.status must be ready, limited or blocked")
    for candidate in pack.get("candidates") or []:
        if not isinstance(candidate, dict):
            errors.append("each candidate must be an object")
            continue
        if candidate.get("disposition") not in DISPOSITIONS:
            errors.append(f"candidate {candidate.get('id')} has an invalid disposition")
        entity = candidate.get("entity") if isinstance(candidate.get("entity"), dict) else {}
        if not all(entity.get(field) for field in ("name", "primary_symbol", "exchange")):
            errors.append(f"candidate {candidate.get('id')} has incomplete listing identity")
        if not candidate.get("supply_chain_position"):
            errors.append(f"candidate {candidate.get('id')} has no supply_chain_position")
        exposure = candidate.get("exposure") if isinstance(candidate.get("exposure"), dict) else {}
        if not exposure.get("description"):
            errors.append(f"candidate {candidate.get('id')} has no exposure description")
        if candidate.get("disposition") == "reject" and not candidate.get("rejection_reasons"):
            errors.append(f"rejected candidate {candidate.get('id')} requires rejection_reasons")
        screen = candidate.get("screen")
        if isinstance(screen, dict) and screen.get("state") not in SCREEN_STATES:
            errors.append(f"candidate {candidate.get('id')} has an invalid screen state")
    try:
        rebuilt = build_funnel(pack)
    except (TypeError, ValueError) as exc:
        errors.append(f"contract invariants could not be recomputed: {exc}")
        return errors
    if pack.get("causal_gate") != rebuilt.get("causal_gate"):
        errors.append("causal_gate does not match required causal-link status and lineage")
    if pack.get("ranking") != rebuilt.get("ranking"):
        errors.append("ranking does not match the recomputed eligible-candidate order")
    if quality.get("status") != rebuilt.get("quality", {}).get("status"):
        errors.append("quality.status does not match recomputed readiness")
    original_candidates = pack.get("candidates") or []
    rebuilt_candidates = rebuilt.get("candidates") or []
    if len(original_candidates) == len(rebuilt_candidates):
        for original, expected in zip(original_candidates, rebuilt_candidates):
            if not isinstance(original, dict) or not isinstance(expected, dict):
                continue
            for field in (
                "evidence_coverage",
                "screen",
                "exposure_lineage_valid",
                "score_lineage_valid",
                "ranking_score",
                "rankable",
                "rankability_reasons",
            ):
                if original.get(field) != expected.get(field):
                    errors.append(
                        f"candidate {original.get('id')} has inconsistent derived field {field}"
                    )
    return errors


def strict_ready(pack: dict[str, Any], errors: list[str] | None = None) -> bool:
    return (
        isinstance(pack, dict)
        and not errors
        and (pack.get("quality") or {}).get("status") == "ready"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--validate-only", action="store_true")
    parser.add_argument("--strict", action="store_true", help="Exit 2 unless quality is ready")
    args = parser.parse_args()
    try:
        raw = json.loads(args.input.read_text(encoding="utf-8"), parse_float=Decimal)
        if args.validate_only:
            errors = validate_funnel(raw)
            result: dict[str, Any] = {"valid": not errors, "errors": errors}
        else:
            result = build_funnel(raw)
            errors = validate_funnel(result)
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
        checked_pack = raw if args.validate_only else result
        if not strict_ready(checked_pack, errors):
            raise SystemExit(2)


if __name__ == "__main__":
    main()
