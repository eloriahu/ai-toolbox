---
name: filing-change-radar
description: Compare two dated company filings for section and numerical changes with page-level provenance. Use for what changed in an annual report, prospectus, risk factors or company disclosure; do not infer materiality from text differences alone.
---

# Filing Change Radar

Use this when the user asks what changed between two filings or whether a new disclosure alters a thesis. First identify the same issuer, filing type, reporting scope and two official dated documents. Prefer issuer/exchange/regulator sources. An optional configured disclosures MCP may locate filings, but never assume it is installed or that every APAC market is covered; respect jurisdiction terms. For local PDFs or Office files, `scripts/filing_extract.py` uses optional Docling to produce page-linked text. A supplied extracted JSON is equally valid. Align stable section keys across versions before comparison; page-number keys alone are provisional when layout changes.

Run `scripts/filing_change.py` on `{"prior": {...}, "current": {...}}` using the [evidence bridge contract](../../references/evidence-bridges.md). Review each flagged section in its source document, verify numbers/tables, and distinguish a wording change from a changed operating fact, forecast, risk or governance commitment. Treat similarity scores and number flags as triage only. State missing pages, extraction/OCR uncertainty and the source dates. Route a full investment thesis assessment to the owning equity workflow; this skill supplies evidence, not a recommendation.

Read-only. Do not run an MCP package without prior configuration or ingest a restricted document contrary to its terms.
