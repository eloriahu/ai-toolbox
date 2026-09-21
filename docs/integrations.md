# Integration matrix

## Installed or directly configured

### Playwright MCP

`research-tools/.mcp.json` starts `@playwright/mcp@0.0.82` in headless mode through a cross-platform Node.js launcher. The launcher uses `npx`, `pnpm`, or Codex's bundled package runner in that order. This is the only upstream executable configured by a plugin manifest. It does not require a repository checkout or stored credentials.

## Optional package integrations

- **browser-use** — pinned in `requirements.optional.lock.txt`; install only when a Python browser agent is specifically needed.
- **OpenBB** — pinned in the finance lock file; authentication remains external and local.
- **yfinance** — pinned in the finance lock file and used by the small `market_snapshot.py` adapter.
- **gs-quant** — pinned in the quant lock file. Services that require Goldman Sachs credentials remain disabled until configured outside Git.

Optional packages are not installed when a Codex plugin is installed. This keeps the marketplace portable and prevents an unrelated project from acquiring a large dependency stack.

## Reference-only integrations

- **Playwright** is the browser engine behind the configured MCP package; use its upstream docs for library-level work.
- **TradingAgents** and **FinGPT** are research frameworks with significant model, data, and runtime choices. The toolbox provides selection guidance, not embedded code.
- **n8n** and **Activepieces** are workflow platforms. Bring an existing self-hosted or managed instance and supply its URL and credentials locally if you later add an adapter.
- **modelcontextprotocol/servers** and **awesome-mcp-servers** are discovery catalogs. Treat every discovered server as untrusted until its source, permissions, data handling, and pinning have been reviewed.

Exact source snapshots are recorded in the root `upstream-lock.json`; no upstream repository is a submodule, subtree, archive, or copied directory.
