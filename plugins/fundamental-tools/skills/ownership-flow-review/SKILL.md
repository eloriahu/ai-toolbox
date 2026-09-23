---
name: ownership-flow-review
description: Normalize APAC disclosed ownership and Taiwan/Korea investor flows with clear dates, categories, units and sources. Use for who owns this, foreign or institutional buying, shareholder changes and positioning checks; do not equate trading flows with beneficial ownership.
---

# Ownership and Flow Review

Route by question. For Taiwan institutional categories, use the read-only FinMind adapter (`FINMIND_TOKEN` required); for Korea daily KRX investor net trading value, use optional local pykrx. Some current pykrx KRX endpoints may require the user's own `KRX_ID` and `KRX_PW`; do not solicit or print them. Both adapters are in `scripts/ownership_flow.py`. Other markets and beneficial-owner claims require dated official disclosed holdings or user-supplied data normalized with `ownership_flow.py build`; optional disclosures MCP can help find source documents only when configured and permitted. Read the [evidence bridge contract](../../references/evidence-bridges.md).

Check symbol, venue, unit, session date, release lag, revisions and source timestamp. FinMind buy/sell rows are shares; pykrx's selected function reports net KRW trading value. Do not add these units or compare them as equivalent. A custodian, nominee, investor category or net-buyer bucket is not necessarily a beneficial owner. Keep holdings and flows as separate lanes in the output. Flow evidence may inform positioning, but never proves a price catalyst or a change in ownership percentage. Label coverage and entitlement gaps rather than filling them with conjecture.
