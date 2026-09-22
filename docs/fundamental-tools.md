# Fundamental tools architecture

`fundamental-tools` separates collection, deterministic research mechanics and investor-facing writing:

```text
filings / user data / optional adapters   theme / move / evidence   draft / prior thesis
                   ↓                               ↓                         ↓
       fundamental_pack/v1                 idea_funnel/v1          research_review/v1
                   └───────────────────────────────┼─────────────────────────┘
                                                   ↓
                          APAC Equity Desk or Public Equity Investing
```

The provider envelope preserves native labels and lineage. Each versioned pack is a stable boundary. Neither downstream plugin needs the source tree or Python package of an upstream integration.

## Reviewed upstreams

| Upstream | Reviewed snapshot | License | Toolbox mode |
| --- | --- | --- | --- |
| `anthropics/financial-services` | `fca3cc8e6c5692ba576b46d7c4783b8443c2a223` | Apache-2.0 | Workflow reference only. No Claude-specific files or recommendation language are copied. |
| [`xbtlin/ai-berkshire`](https://github.com/xbtlin/ai-berkshire/tree/c2508c23b4835d3e5460f113364d25f66d23782b) | `c2508c23b4835d3e5460f113364d25f66d23782b` | [MIT](https://github.com/xbtlin/ai-berkshire/blob/c2508c23b4835d3e5460f113364d25f66d23782b/LICENSE) | Workflow-pattern reference for idea funnels, management delivery, thesis comparison and multi-agent research discipline. No source code, investor-persona claims or performance claims are vendored. |
| `JerBouma/FinanceToolkit` | `9fa19f9e97fee229dad4d65cf9c1448597af5df5` | MIT | Optional local calculation/provider package, pinned at `2.2.0`. |
| `JerBouma/FinanceDatabase` | `d0b95bd51f9c594c81bac0b20c7ab6cbd084c51e` | MIT | Optional issuer/identifier package, pinned at `2.4.0`. |
| `J-Quants/jquants-api-client-python` | `edbf19e59059ff62a3f66f072aaa0ef643009344` | Apache-2.0 | Optional official Japan API client, pinned at `2.7.0`. |
| `J-Quants/jquants-cli` | `2ce5c9ef3eac21fbf283f76b677ba363f2fce343` | MIT | Reference CLI; not executed by the toolbox adapter. |
| `FinanceData/OpenDartReader` | `9969a8cda25192e7b4d6c277411d62d8aa8cfa84` | MIT | Optional Korea FSS API wrapper, pinned at `0.3.3`. |
| `NanookAI/twse-api` | `2999e3c32977d33c51c94c245cdfe49a672f3281` | MIT | Endpoint/convention reference; runtime calls the official TWSE OpenAPI directly. |
| `dgunning/edgartools` | `4e817de7bf3efae44024e168754e8f5d53b1a227` | MIT | Optional SEC EDGAR/XBRL package, pinned at `5.58.0`. |
| `akfamily/akshare` | `0191689d57c667b7c7a198fd0cf97316837ef311` | MIT | Optional China/HK fallback, pinned at `1.18.97`. |

The exact pins are machine-validated in `upstream-lock.json`. Licenses and data-service terms remain those of each upstream. A permissive software license does not grant access to paid APIs, redistribute provider data or override exchange/regulator terms.

The `ai-berkshire` concepts were independently adapted into versioned, dependency-free contracts and new implementations. Attribution is retained under its MIT license; the toolbox does not execute that repository or present its stated investment results as validation.

## Runtime policy

- Core pack and valuation calculations use the Python standard library.
- Optional packages are lazy imports and live in provider-specific environments.
- Credentials are read from environment variables only. Capability checks return `configured` or `not_configured`, never a value.
- Live collectors are read-only and preserve their raw provider output before normalization.
- Official sources outrank calculation libraries and aggregators.
- Installation remains a user choice; the plugin never installs a dependency during research.
- All three skills allow implicit invocation after one plugin install. Their discriminating descriptions let the model select fundamentals, idea generation or quality review from a natural-language request without running every workflow.
- `idea_funnel.py` uses only explicit scoring weights and sector/profile rules. It preserves insufficient and not-applicable screen states, every rejection reason and unrankable candidates.
- `research_review.py` uses decimal arithmetic for management targets and report-number comparison. Required audits block publication if any declared critical field is missing, failed or unverifiable, or if zero fields are verified.
- Source registries identify direct upstream origin and independence groups so repeated reporting is not counted as corroboration.

## Public Equity Investing

The installed Public Equity Investing plugin supplies mature deliverable owners for initiating coverage, financial normalization, three-statement models, DCF, comps, earnings, thesis tracking and memos. This toolbox does not duplicate those presentation workflows. It supplies the APAC-aware provider, idea-generation mechanics and research-control substrate they can consume, while APAC Equity Desk owns regional conventions and sell-side desk writing.
