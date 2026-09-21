# Integration matrix

The lock file uses five classifications: runtime dependency, MCP integration, optional dependency, reference-only and external service. Classification describes what the toolbox actually does today, not what an upstream project could support later.

| Upstream | Toolbox group | Classification | Current integration |
| --- | --- | --- | --- |
| `microsoft/playwright` | `research-tools` | Runtime dependency | Browser engine reached transitively through the configured MCP package. |
| `microsoft/playwright-mcp` | `research-tools` | MCP integration | Pinned `@playwright/mcp@0.0.82`, launched headlessly through the cross-platform runner. |
| `browser-use/browser-use` | `research-tools` | Optional dependency | Pinned Python package for tasks that materially need a Python browser agent. |
| `OpenBB-finance/OpenBB` | `finance-tools` | Optional dependency | Broader provider and standardized-query layer; install only for tasks that need it. |
| `ranaroussi/yfinance` | `finance-tools` | Optional dependency | Powers the versioned, provenance-rich market snapshot adapter. |
| `anthropics/financial-services` | `fundamental-tools` | Reference-only | Workflow patterns for coverage, earnings, model updates, comps and DCF; Claude-specific and US-centric constraints are not imported. |
| `JerBouma/FinanceToolkit` | `fundamental-tools` | Optional dependency | Local calculation and provider-routing engine; underlying source lineage remains explicit. |
| `JerBouma/FinanceDatabase` | `fundamental-tools` | Optional dependency | Cross-market issuer/ticker/identifier discovery, not a live fundamental source. |
| `J-Quants/jquants-api-client-python` | `fundamental-tools` | Optional dependency | Official Japan API client for financial summaries, details and valuation. Requires a plan and API key. |
| `J-Quants/jquants-cli` | `fundamental-tools` | Reference-only | Official JSON-capable CLI alternative; the Python adapter is the supported toolbox path. |
| `FinanceData/OpenDartReader` | `fundamental-tools` | Optional dependency | Korea FSS OpenDART wrapper for financial statements and disclosures. |
| `NanookAI/twse-api` | `fundamental-tools` | Reference-only | Reviewed endpoint/convention reference; the toolbox calls the official TWSE OpenAPI directly. |
| `dgunning/edgartools` | `fundamental-tools` | Optional dependency | SEC filing and XBRL access for US issuers and APAC ADRs. |
| `akfamily/akshare` | `fundamental-tools` | Optional dependency | China/HK public-web fallback; upstream website lineage and endpoint-drift warnings are retained. |
| `TauricResearch/TradingAgents` | `finance-tools` | Reference-only | Experimental financial-research framework; no models, data stack or runtime are embedded. |
| `AI4Finance-Foundation/FinGPT` | `finance-tools` | Reference-only | Optional financial-NLP framework; no model weights or runtime are embedded. |
| `goldmansachs/gs-quant` | `quant-tools` | Optional dependency | Advanced analytics when credentials and data access are configured externally. |
| `n8n-io/n8n` | `automation-tools` | Reference-only | Primary future workflow platform; no service or account is provisioned. |
| `activepieces/activepieces` | `automation-tools` | Reference-only | Alternative/fallback when a workflow specifically fits it better. |
| `modelcontextprotocol/servers` | `research-tools`, `automation-tools` | Reference-only | MCP discovery catalog, never an automatic install source. |
| `punkpeye/awesome-mcp-servers` | `research-tools`, `automation-tools` | Reference-only | Community discovery catalog, never an automatic install source. |

The toolbox does not provision or manage an external service. Optional packages are not installed with a plugin, and reference-only projects are not vendored or executed. Exact source snapshots are recorded in `upstream-lock.json`.

`fundamental-tools/scripts/provider_adapters.py` produces a raw, provenance-rich adapter envelope. `fundamental-tools/scripts/fundamental_pack.py` is the separate normalization/calculation boundary. Keeping collection and calculation separate prevents an aggregator or calculation library from silently becoming the authoritative filing source.

`plugins/research-tools/.mcp.json` is the only directly executable integration. Its launcher uses `npx`, `pnpm`, or Codex's bundled package runner in that order. On first use, the selected runner may download the pinned package.

The yfinance snapshot schema records provenance, adjustment settings, market metadata availability, null counts and price rows. `quant-tools/scripts/return_metrics.py` consumes this JSON directly.
