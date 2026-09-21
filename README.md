# AI Toolbox

`ai-toolbox` is a lightweight Codex plugin marketplace for reusable research, finance, quantitative-analysis, and automation workflows. It is deliberately an integration layer: upstream projects stay upstream, and this repository contains only manifests, pinned dependency metadata, small adapters, and documentation.

## What is included

| Plugin | Ready after plugin install | Optional local packages | Reference-only projects |
| --- | --- | --- | --- |
| `research-tools` | Playwright MCP and source-evidence matrix | `browser-use==0.13.10` | Playwright, MCP Servers, Awesome MCP Servers |
| `finance-tools` | Workflow skill and yfinance market snapshot | `openbb==4.7.2`, `yfinance==1.7.0` | — |
| `quant-tools` | Dependency-free return and drawdown metrics | `gs-quant==2.1.16` | TradingAgents, FinGPT |
| `automation-tools` | Safety-aware portable workflow validator | None | n8n, Activepieces, MCP Servers |

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

## Credentials and local configuration

No secrets belong in this repository. Copy [`.env.example`](.env.example) to `.env` only if an integration you explicitly enable requires credentials. `.env` files, virtual environments, package caches, and generated data are ignored by Git.

## Use from `eloriahu/apac-equity-desk`

Install this marketplace once at the user or workspace level, then enable the desired toolbox plugins while working in `apac-equity-desk`. The desk repository does not need a copy, submodule, subtree, or vendored dependency. See [`docs/apac-equity-desk.md`](docs/apac-equity-desk.md) for the recommended boundary and an optional project note.

No change to `apac-equity-desk` is required, so this repository intentionally leaves that project untouched.

## Updating pins

Every upstream repository has an exact commit and default branch in [`upstream-lock.json`](upstream-lock.json). Review upstream release notes and security posture before changing a pin. Package pins and git pins are independent: update both when the package release is meant to track a newer source revision.

## Validate the repository

The repository's checks have no third-party Python dependencies:

```shell
python scripts/validate_repo.py
python -m unittest discover -s tests -v
```

GitHub Actions runs the same structural, unit, compilation, and Node.js syntax checks on every push and pull request.

## License

The integration layer is MIT licensed. Every upstream project keeps its own license, terms, trademarks, and support policy.
