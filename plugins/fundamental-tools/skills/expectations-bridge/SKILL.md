---
name: expectations-bridge
description: Compare dated consensus or analyst-model snapshots on a like-for-like basis. Use for estimate revisions, what changed in expectations after earnings, guidance versus consensus, or what is priced in; require comparable period, currency, basis and provider.
---

# Expectations Bridge

Use two timestamped snapshots from the same issuer, listing and provider, preferably user-supplied Bloomberg/model exports with provenance. Map every row to metric, fiscal period, reported/adjusted basis, currency, unit, statistic, value and source IDs. Run `scripts/expectations_bridge.py` using the [evidence bridge contract](../../references/evidence-bridges.md). It performs exact-decimal like-for-like deltas and keeps new/dropped rows separate; missing overlap is a gap, not a zero revision.

Interpret the revisions only after checking what was known at each snapshot time, consensus contributor/sample changes, reporting-period rollovers and management guidance. Keep estimate revision, actual-versus-consensus surprise and stock-price reaction separate. Do not claim that one caused the other without independent dated evidence. For a full model or valuation workbook, pass the verified bridge to Public Equity Investing when available.
