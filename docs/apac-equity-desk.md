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

This avoids duplicated source and lets future US-equity, personal research, and quant projects use the same integrations. It also allows toolbox updates without changing the desk repository.

An optional one-line note in the desk README may link to `https://github.com/eloriahu/ai-toolbox`, but it is not required for the integration to work. This initial setup therefore makes no change to `apac-equity-desk`.
