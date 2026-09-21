"""Validate a portable workflow specification and summarize its risk gates."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


RISK_LEVELS = {"read", "reversible-write", "external-write", "destructive"}
APPROVAL_RISKS = {"external-write", "destructive"}


def validate_workflow(spec: dict) -> dict:
    if not isinstance(spec, dict):
        raise ValueError("Workflow must be a JSON object.")
    name = _text(spec, "name", "workflow")
    trigger = spec.get("trigger")
    if not isinstance(trigger, dict):
        raise ValueError("Workflow requires a 'trigger' object.")
    _text(trigger, "type", "trigger")

    steps = spec.get("steps")
    if not isinstance(steps, list) or not steps:
        raise ValueError("Workflow requires a non-empty 'steps' array.")

    seen_ids = set()
    approval_steps = []
    risk_counts = {risk: 0 for risk in sorted(RISK_LEVELS)}
    for position, step in enumerate(steps, start=1):
        if not isinstance(step, dict):
            raise ValueError(f"Step {position} must be an object.")
        step_id = _text(step, "id", f"step {position}")
        _text(step, "action", f"step {position}")
        if step_id in seen_ids:
            raise ValueError(f"Duplicate step id: {step_id}")
        seen_ids.add(step_id)
        risk = step.get("risk")
        if risk not in RISK_LEVELS:
            raise ValueError(
                f"Step '{step_id}' risk must be one of: {', '.join(sorted(RISK_LEVELS))}."
            )
        risk_counts[risk] += 1
        if risk in APPROVAL_RISKS:
            if step.get("approval_required") is not True:
                raise ValueError(
                    f"Step '{step_id}' with risk '{risk}' must set approval_required=true."
                )
            approval_steps.append(step_id)

    return {
        "name": name,
        "valid": True,
        "stepCount": len(steps),
        "approvalSteps": approval_steps,
        "riskCounts": risk_counts,
    }


def _text(obj: dict, field: str, context: str) -> str:
    value = obj.get(field)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{context} requires a non-empty '{field}' string.")
    return value.strip()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("workflow_json")
    args = parser.parse_args()
    try:
        data = json.loads(Path(args.workflow_json).read_text(encoding="utf-8"))
        result = validate_workflow(data)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        raise SystemExit(str(exc)) from exc
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
