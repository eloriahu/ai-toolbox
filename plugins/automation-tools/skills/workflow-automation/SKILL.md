---
name: workflow-automation
description: Design safe, portable workflow automations for n8n, Activepieces, or reviewed MCP servers without bundling or provisioning those services.
---

# Workflow Automation

Use this skill to turn a manual process into a reviewable automation design.

## Workflow

1. Describe the trigger, inputs, transformations, outputs, retries, idempotency, and owner.
2. Classify each step as read-only, reversible write, or destructive/externally visible action.
3. Choose n8n or Activepieces only after comparing deployment, connector, governance, and maintenance needs.
4. Keep credentials in the workflow platform's secret store, not in exported workflow JSON or this repository.
5. Add dry-run behavior, logging, rate limits, error handling, and an approval step for consequential actions.
6. Produce a platform-neutral flow before writing platform-specific nodes or pieces.

## Integration boundaries

- n8n and Activepieces are reference-only; this plugin does not start a service or connect an account.
- MCP catalogs are discovery sources, not trusted packages. Review any server before installation.
- Do not enable a write-capable connector or send external messages without explicit user authorization.
