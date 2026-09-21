# Using AI Toolbox with `apac-equity-desk`

Keep the repositories separate:

```text
Codex user/workspace
├── installed marketplace: eloriahu/ai-toolbox
│   ├── research-tools
│   ├── finance-tools
│   ├── fundamental-tools
│   ├── quant-tools
│   └── automation-tools
└── project: eloriahu/apac-equity-desk
```

1. Install `ai-toolbox` as a Codex marketplace once.
2. Install or enable only the plugin groups needed for the current desk task.
3. Open `apac-equity-desk` as the project and invoke the installed toolbox skills/tools there.
4. Keep desk-specific house style, templates, and workflow logic in `apac-equity-desk`.
5. Keep general adapters, pins, and reusable integration guidance here.

## Loose-coupling contract

- `apac-equity-desk` remains usable with user-supplied Bloomberg packs and its dependency-free calculation helpers when no toolbox plugin is available.
- `research-tools` may collect public filings and web evidence, but the desk retains its APAC source hierarchy, causal standards and house style.
- `finance-tools` normalizes Bloomberg exports and screenshot transcriptions and may fill explicit market-data gaps through OpenBB; provider output must still be mapped into the desk contract with field-level lineage and may not silently replace a fresh conflicting observation.
- `fundamental-tools` produces `fundamental_pack/v1` from traceable statements, optional country adapters and transparent calculations. The desk owns APAC interpretation, house style, causal wording and final source verification.
- `quant-tools` may perform reusable statistics and risk calculations. APAC-specific peer baskets, A/H conventions and market mappings remain in the desk.
- `automation-tools` may prepare research packs or drafts. It must not publish externally, alter alerts/watchlists or perform brokerage mutations without a separately authorized workflow.
- `finance-tools/scripts/event_calendar.py` normalizes an already sourced event set. Event discovery, APAC relevance and house presentation remain desk responsibilities.
- `automation-tools/examples/apac-sector-radar-workflow.json` defines the portable schedule/read/rank/local-write/approval flow; the desk owns `topic_radar.py`, sector baskets and the causal investigation.
- Missing optional capabilities produce a declared data gap or a reduced-scope draft, not an installation attempt or invented result.
- The installed Public Equity Investing plugin may own broader initiations, model updates, comps, DCFs or thesis trackers. `fundamental-tools` remains the reusable source/calculation layer, and APAC Equity Desk remains the APAC note owner.

This avoids duplicated source and lets future US-equity, personal research, and quant projects use the same integrations. It also allows toolbox updates without changing the desk repository.

An optional one-line note in the desk README may link to `https://github.com/eloriahu/ai-toolbox`, but it is not required for the integration to work. The repositories share data contracts and installed capabilities, not source trees or hard package dependencies.
