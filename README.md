# AI Toolbox

`ai-toolbox` is a Codex plugin marketplace for research, market data, company fundamentals, quantitative analysis and workflow design. It keeps reusable integrations in one repository so projects such as [APAC Equity Desk](https://github.com/eloriahu/apac-equity-desk) can consume them without copying source code.

Upstream projects stay upstream. This repository contains reviewed manifests, exact dependency pins, small read-only adapters, data contracts and tests.

## What can I use it for?

| Request | Plugin | Result |
| --- | --- | --- |
| “Research this topic and show which source supports each claim” | `research-tools` | Browser evidence with a compact source matrix |
| “Normalize this Bloomberg export and fill only missing fields” | `finance-tools` | A timestamped market pack with field-level provider lineage |
| “Build a one-year market snapshot for 7203 JP” | `finance-tools` | Reproducible price history with currency, adjustment and missing-data metadata |
| “Run a fundamental review of 9988 HK” | `fundamental-tools` | An auditable `fundamental_pack/v1` with financial history, ratios, valuation and data gaps |
| “AI power demand is rising—where is the real bottleneck and which listed names matter?” | `fundamental-tools` | A causal, screenable `idea_funnel/v1` with ranked and explicitly rejected candidates |
| “This stock is up—what are the second-order implications?” | `fundamental-tools` | Catalyst-linked supplier, peer, customer and substitution ideas with falsifiers |
| “Did management deliver, and did our thesis actually change?” | `fundamental-tools` | A `research_review/v1` covering researchability, promises and fact/price/wording drift |
| “Audit every important number before this report goes out” | `fundamental-tools` | Decimal-safe critical-field verification and a publication gate |
| “What changed between these two annual reports?” | `fundamental-tools` | A page- and source-linked `filing_change/v1` review queue; optional Docling extraction for local PDFs |
| “How did FY27 consensus change after results?” | `fundamental-tools` | An exact-decimal `expectations_bridge/v1` that keeps different bases, periods and currencies apart |
| “Are foreign investors buying 2330 TW?” | `fundamental-tools` | A dated `ownership_flow/v1` with Taiwan category flows, plus separate disclosed holdings when supplied |
| “Show Korean institutional flow for 005930” | `fundamental-tools` | Optional pykrx net trading value in KRW, clearly separate from ownership |
| “Pull official Japanese financials for 7203” | `fundamental-tools` | J-Quants statement, detail and valuation records when credentials are configured |
| “Fetch TSMC’s latest TWSE profitability data” | `fundamental-tools` | Official TWSE records with their original Chinese field names |
| “Resolve this issuer across exchanges and identifiers” | `fundamental-tools` | FinanceDatabase security-master candidates for verification |
| “Compare return, volatility and drawdown for these securities” | `quant-tools` | Repeatable statistics from a normalized price pack |
| “Design a scheduled sector-radar workflow without publishing automatically” | `automation-tools` | A portable, approval-gated workflow specification |

## How the pieces fit

```text
public sources / user exports / optional provider packages
                         │
             research-tools and finance-tools
                         │
              fundamental-tools and quant-tools
                         │
       normalized packs with timestamps and source lineage
                         │
       APAC Equity Desk / Public Equity Investing / your project
```

The toolbox handles collection, normalization and deterministic calculations. The consuming project owns its research judgment, writing style and final review.

## Included plugins

| Plugin | Works after plugin installation | Optional packages or services |
| --- | --- | --- |
| `research-tools` | Source-evidence matrix and configured Playwright MCP launcher | `browser-use==0.13.10` |
| `finance-tools` | Bloomberg input normalization, market-pack merging and event normalization | `openbb==4.7.2`, `yfinance==1.7.0` |
| `fundamental-tools` | `fundamental_pack/v1`, `idea_funnel/v1`, `research_review/v1`, filing/expectations/ownership-flow bridges, ratio/DCF calculations, source-quality controls, capability checks and direct TWSE/FinMind access | FinanceToolkit, FinanceDatabase, J-Quants, OpenDART, EdgarTools, AKShare, Docling and pykrx |
| `quant-tools` | Return, volatility and drawdown calculations | `gs-quant==2.1.16` |
| `automation-tools` | Workflow validation and approval-gated APAC radar examples | n8n or Activepieces when separately selected |

Reference-only repositories are pinned and documented but never installed, executed or copied into the toolbox. See [the integration matrix](docs/integrations.md) and [exact upstream locks](upstream-lock.json).

Filing lookup through disclosures MCP is a configured, optional route—not a bundled server. Docling and pykrx are separate optional packages; FinMind requires the user's token, and some current KRX endpoints may require the user's own KRX login. A flow report is not a beneficial-ownership register or proof of a price catalyst.

## Install in Codex

Add the marketplace once, then install only the plugins you need:

```shell
codex plugin marketplace add https://github.com/eloriahu/ai-toolbox.git
codex plugin add research-tools@ai-toolbox
codex plugin add finance-tools@ai-toolbox
codex plugin add fundamental-tools@ai-toolbox
codex plugin add quant-tools@ai-toolbox
codex plugin add automation-tools@ai-toolbox
```

For an APAC equity research setup, install `research-tools`, `finance-tools`, `fundamental-tools` and `quant-tools`. `automation-tools` is optional.

`research-tools` is desktop-only because it declares a local MCP server. On first use, its launcher may download the pinned Playwright MCP package through the available package runner.

## Fundamental research

`fundamental-tools` separates provider output from the normalized research pack:

```text
provider response
      ↓
fundamental_adapter_output/v1
      ↓
normalization and transparent calculations
      ↓
fundamental_pack/v1
```

Check the current machine before choosing a provider:

```shell
python plugins/fundamental-tools/scripts/provider_adapters.py capabilities
```

Example provider calls:

```shell
# Taiwan: official TWSE OpenAPI, no key required
python plugins/fundamental-tools/scripts/provider_adapters.py twse --code 2330 --statement profitability --output twse.json

# Japan: J-Quants API key required
python plugins/fundamental-tools/scripts/provider_adapters.py jquants --code 7203 --output jquants.json

# Korea: OpenDART API key required
python plugins/fundamental-tools/scripts/provider_adapters.py opendart --corp 005930 --year 2025 --output dart.json
```

Build and validate a normalized company pack:

```shell
python plugins/fundamental-tools/scripts/fundamental_pack.py company-input.json --output fundamental-pack.json --strict
```

The calculator covers growth, margins, free cash flow, cash conversion, ROE, ROA, ROIC, leverage, interest coverage, market multiples and named DCF scenarios. It refuses invalid WACC/terminal-growth relationships and marks missing evidence instead of inventing values.

Read [the fundamental architecture and license review](docs/fundamental-tools.md) for the full provider hierarchy and contract boundary.

### Idea generation and research review

The same plugin can automatically route a natural request to two additional skills; users do not need to remember a chain of commands.

```text
theme, event or verified stock move
             ↓
causal chain → supply-chain constraint → listed universe
             ↓
explicit sector/income screens + evidence lanes
             ↓
idea_funnel/v1: ranked, watched and rejected candidates

research draft or prior thesis
             ↓
researchability + management promises + thesis drift + number audit
             ↓
research_review/v1: confidence limits and publication gate
```

`equity-idea-generation` is considered for bottleneck, theme-to-name and second-order implication questions. `research-quality-review` is considered for management delivery, thesis changes, source confidence and numerical audits. Both allow implicit invocation, but their descriptions are intentionally distinct so a simple fundamentals request does not launch the full idea-and-audit stack.

The screen engine accepts explicit sector or user-supplied rules; it has no universal ROE, leverage, margin or payout cutoffs. It preserves `not_applicable` and `insufficient` states and supports income-durability inputs such as distribution coverage, free cash flow, leverage and payout history without generating position sizes or orders.

```shell
python plugins/fundamental-tools/scripts/idea_funnel.py idea-input.json --output idea-funnel.json --strict
python plugins/fundamental-tools/scripts/research_review.py review-input.json --output research-review.json --strict
```

See the [`idea_funnel/v1` contract](plugins/fundamental-tools/references/idea-funnel.md) and [`research_review/v1` contract](plugins/fundamental-tools/references/research-review.md).

## Market-data workflow

Normalize a Bloomberg export or a JSON transcription of a visible screenshot:

```shell
python plugins/finance-tools/scripts/normalize_market_input.py bloomberg.csv --source-kind bloomberg_export --data-as-of 2026-09-21T13:04:00+08:00 --market HK --output bloomberg-pack.json
```

When OpenBB is configured, fill missing or stale fields without overwriting a fresh primary observation:

```shell
python plugins/finance-tools/scripts/openbb_market_snapshot.py --markets APAC --provider fmp --output openbb-pack.json
python plugins/finance-tools/scripts/merge_market_sources.py bloomberg-pack.json openbb-pack.json --expected-market-timestamp 2026-09-21T13:04:00+08:00 --output merged-pack.json
```

Calculate return statistics from a public snapshot:

```shell
python plugins/finance-tools/scripts/market_snapshot.py 7203.T --period 1y --output snapshot.json
python plugins/quant-tools/scripts/return_metrics.py snapshot.json --output metrics.json
```

## Optional Python environments

Plugin installation does not install Python packages. Create isolated environments only for the integrations you plan to use.

```shell
python -m venv .venv
.venv/Scripts/python -m pip install -r plugins/finance-tools/requirements.lock.txt
```

Fundamental providers use separate lock files:

- `requirements.core.lock.txt`: FinanceToolkit and FinanceDatabase
- `requirements.jp.lock.txt`: J-Quants
- `requirements.kr.lock.txt`: OpenDartReader
- `requirements.us.lock.txt`: EdgarTools
- `requirements.cn.lock.txt`: AKShare

OpenDartReader 0.3.3 requires Python 3.13. Keep it in a separate environment when the main finance environment uses an older interpreter.

## APAC Equity Desk and Public Equity Investing

[APAC Equity Desk](https://github.com/eloriahu/apac-equity-desk) consumes `fundamental_pack/v1` and market packs. It adds APAC source priority, market conventions, evidence-ranked catalyst work and desk writing.

The optional Public Equity Investing plugin can own larger deliverables such as initiating coverage, comps, DCF workbooks, model updates and thesis trackers. `fundamental-tools` remains the source, calculation, idea-funnel and research-control layer, so those workflows do not need a second set of provider adapters.

The repositories share contracts, not source trees, submodules or hidden local paths. See [the APAC integration notes](docs/apac-equity-desk.md).

## Credentials and safety

Copy [`.env.example`](.env.example) to `.env` only when a selected provider requires it. Never commit the resulting file.

Capability reports reveal whether a credential is configured but never return its value. Bloomberg screenshots and exports stay local. Hosted MCP services require a separate review before receiving credentials or proprietary inputs.

All integrations are research-only. The toolbox does not place orders, modify brokerage accounts, publish research or provision external services.

## Validate the repository

The repository checks do not require the optional finance packages:

```shell
python scripts/validate_repo.py
python -m unittest discover -s tests -v
```

GitHub Actions runs the same structural, unit, compilation and Node.js syntax checks on every push and pull request.

## License

The integration layer is MIT licensed. Each upstream project retains its own license, terms, trademarks and support policy. A software license does not grant access to paid data or permission to redistribute provider content.
