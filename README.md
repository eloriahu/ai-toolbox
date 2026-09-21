# AI Toolbox

`ai-toolbox` is a lightweight Codex plugin marketplace for reusable research, finance, quantitative-analysis, and automation workflows. It is deliberately an integration layer: upstream projects stay upstream, and this repository contains only manifests, pinned dependency metadata, small adapters, and documentation.

## What is included

| Plugin | Ready after plugin install | Optional local packages | Reference-only projects |
| --- | --- | --- | --- |
| `research-tools` | Playwright MCP and source-evidence matrix | `browser-use==0.13.10` | MCP Servers, Awesome MCP Servers |
| `finance-tools` | Bloomberg export/screenshot normalization, field-level OpenBB fallback, market snapshots and event calendars | `openbb==4.7.2`, `yfinance==1.7.0` | TradingAgents, FinGPT |
| `quant-tools` | CSV/snapshot return and drawdown metrics | `gs-quant==2.1.16` | — |
| `automation-tools` | Safety-aware workflow validator and approval-gated APAC radar design | None | n8n (primary), Activepieces (fallback), MCP Servers |

“Reference-only” means the project is documented and pinned in [`upstream-lock.json`](upstream-lock.json), but no code, service, container, account, or credentials are installed by this repository.

## Install in Codex

Add this GitHub repository as a marketplace, then install only the groups you want:

```shell
codex plugin marketplace add https://github.com/eloriahu/ai-toolbox.git
codex plugin add research-tools@ai-toolbox
codex plugin add finance-tools@ai-toolbox
codex plugin add quant-tools@ai-toolbox
codex plugin add automation-tools@ai-toolbox
```

The marketplace format follows the [official OpenAI plugin-management documentation](https://learn.chatgpt.com/docs/enterprise/plugin-management). In a managed ChatGPT workspace, an admin can instead import `https://github.com/eloriahu/ai-toolbox` under **Admin → Plugins → Add → Import marketplace**.

`research-tools` is desktop-only because it declares a local MCP server. It requires Node.js and uses a small launcher that selects `npx`, `pnpm`, or Codex's bundled package runner. On first use, the selected runner may download the pinned `@playwright/mcp` package. The other plugins contain reusable instructions and optional dependency files; they do not install third-party runtimes automatically.

## Optional dependencies

Create an isolated environment for the plugin you want to use. The lock files are intentionally separate so installing finance data tools does not pull in quant or browser stacks.

```shell
python -m venv .venv
.venv/Scripts/python -m pip install -r plugins/finance-tools/requirements.lock.txt
```

On macOS/Linux, use `.venv/bin/python` instead. See [`docs/integrations.md`](docs/integrations.md) for every upstream and its support level.

The finance and quant adapters form a repeatable file-based pipeline:

```shell
python plugins/finance-tools/scripts/market_snapshot.py 7203.T --period 1y --output snapshot.json
python plugins/quant-tools/scripts/return_metrics.py snapshot.json --output metrics.json
```

Snapshots state whether prices were auto-adjusted and retain provider, retrieval time, currency, exchange time zone, and missing-data context. For weekly or monthly data, pass an appropriate `--periods-per-year` value to the metrics command.

Normalize a user-supplied Bloomberg CSV/JSON export—or JSON transcribed from a Bloomberg screenshot—without confusing upload time with market time:

```shell
python plugins/finance-tools/scripts/normalize_market_input.py bloomberg.csv --source-kind bloomberg_export --data-as-of 2026-09-21T13:04:00+08:00 --market HK --output bloomberg-pack.json
```

When configured, fetch a broad APAC fallback through OpenBB and merge only missing or stale live fields while retaining per-field lineage:

```shell
python plugins/finance-tools/scripts/openbb_market_snapshot.py --markets APAC --provider fmp --output openbb-pack.json
python plugins/finance-tools/scripts/merge_market_sources.py bloomberg-pack.json openbb-pack.json --expected-market-timestamp 2026-09-21T13:04:00+08:00 --output merged-pack.json
```

Bloomberg screenshots and exports remain local and must not be committed or redistributed.

Normalize a sourced market-event set without adding a live service:

```shell
python plugins/finance-tools/scripts/event_calendar.py events.json --days 7 --output next-events.json
```

`automation-tools/examples/apac-sector-radar-workflow.json` is a portable design for scheduled, read-only topic capture. It writes a local evidence pack and leaves its optional publication step disabled by default and human-approval gated. The repository does not provision n8n, Activepieces, credentials, a quote feed, or a background service.

## Credentials and local configuration

No secrets belong in this repository. Copy [`.env.example`](.env.example) to `.env` only if an integration you explicitly enable requires credentials. `.env` files, virtual environments, package caches, and generated data are ignored by Git.

## Use from `eloriahu/apac-equity-desk`

Install this marketplace once at the user or workspace level, then enable the desired toolbox plugins while working in `apac-equity-desk`. The desk repository does not need a copy, submodule, subtree, or vendored dependency. See [`docs/apac-equity-desk.md`](docs/apac-equity-desk.md) for the recommended boundary and an optional project note.

No change to `apac-equity-desk` is required, so this repository intentionally leaves that project untouched.

## Updating pins

Every upstream repository has an exact commit, default branch, owning plugin group and integration classification in [`upstream-lock.json`](upstream-lock.json). The allowed classifications are runtime dependency, MCP integration, optional dependency, reference-only and external service. Review upstream release notes and security posture before changing a pin. Package pins and git pins are independent: update both when the package release is meant to track a newer source revision.

## Validate the repository

The repository's checks have no third-party Python dependencies:

```shell
python scripts/validate_repo.py
python -m unittest discover -s tests -v
```

GitHub Actions runs the same structural, unit, compilation, and Node.js syntax checks on every push and pull request.

## License

The integration layer is MIT licensed. Every upstream project keeps its own license, terms, trademarks, and support policy.
