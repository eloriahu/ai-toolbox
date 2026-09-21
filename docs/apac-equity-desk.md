# Using AI Toolbox with `apac-equity-desk`

Keep the repositories separate:

```text
Codex user/workspace
├── installed marketplace: eloriahu/ai-toolbox
│   ├── research-tools
│   ├── finance-tools
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

- `apac-equity-desk` remains usable with Longbridge, supplied evidence packs and its dependency-free calculation helpers when no toolbox plugin is available.
- `research-tools` may collect public filings and web evidence, but the desk retains its APAC source hierarchy, causal standards and house style.
- `finance-tools` may supply normalized public-market data or evaluate broader research frameworks; provider output must still be mapped into the desk's data contract and may not silently replace a conflicting observation.
- `quant-tools` may perform reusable statistics and risk calculations. APAC-specific peer baskets, A/H conventions and market mappings remain in the desk.
- `automation-tools` may prepare research packs or drafts. It must not publish externally, alter alerts/watchlists or perform brokerage mutations without a separately authorized workflow.
- Missing optional capabilities produce a declared data gap or a reduced-scope draft, not an installation attempt or invented result.

This avoids duplicated source and lets future US-equity, personal research, and quant projects use the same integrations. It also allows toolbox updates without changing the desk repository.

An optional one-line note in the desk README may link to `https://github.com/eloriahu/ai-toolbox`, but it is not required for the integration to work. The repositories share data contracts and installed capabilities, not source trees or hard package dependencies.
