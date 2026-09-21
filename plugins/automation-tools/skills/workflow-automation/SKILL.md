---
name: workflow-automation
description: Design safe, portable workflow automations for n8n, Activepieces, or reviewed MCP servers without bundling or provisioning those services.
---

# Workflow Automation

Use this skill to turn a manual process into a reviewable automation design.

## Workflow

1. Describe the trigger, inputs, transformations, outputs, retries, idempotency, and owner.
2. Classify each step as read-only, reversible write, or destructive/externally visible action.
3. Prefer n8n as the default future workflow platform. Choose Activepieces only when its deployment, connector, governance or maintenance fit is materially better for the specific workflow.
4. Keep credentials in the workflow platform's secret store, not in exported workflow JSON or this repository.
5. Express the platform-neutral flow as JSON and validate it with `scripts/validate_workflow.py`; start from `examples/workflow-spec.json` when useful.
6. Add dry-run behavior, logging, rate limits, error handling, and an approval step for consequential actions.
7. Produce platform-specific nodes or pieces only after the portable flow passes validation.

For a scheduled APAC topic scan, start from `examples/apac-sector-radar-workflow.json`. It creates a local evidence pack, not a publication subscription. Its optional external-write step is disabled by default and requires a fresh human approval for the selected draft.

## Integration boundaries

- n8n and Activepieces are reference-only; this plugin does not start a service or connect an account. Do not configure or run both for the same workflow by default.
- MCP catalogs are discovery sources, not trusted packages. Review any server before installation.
- Do not enable a write-capable connector or send external messages without explicit user authorization.

The validator accepts four risk levels: `read`, `reversible-write`, `external-write`, and `destructive`. The latter two must set `approval_required` to `true`.
