# Provider selection

Choose the narrowest authoritative route that supports the requested fields. Preserve field-level lineage when combining sources.

| Priority | Market/use | Preferred route | Role and limitations |
| --- | --- | --- | --- |
| 1 | Any | User-provided Bloomberg/model export; company IR; exchange/regulator filing | Primary evidence. Record the displayed/report timestamp separately from task time. |
| 2 | Japan | J-Quants API | Official JPX service. API key and plan required; fields are plan-aware. |
| 2 | Korea | OpenDART via OpenDartReader | Official FSS disclosure service. `DART_API_KEY` required. |
| 2 | Taiwan | TWSE OpenAPI | Official snapshot endpoints; no API key, no arbitrary historical query for most datasets, and industry-specific statement schemas. |
| 2 | US/ADR | SEC EDGAR via EdgarTools | Official SEC filings and XBRL. Set the SEC-compliant identity required by the upstream service. |
| 3 | Cross-market identity | FinanceDatabase | Security master and discovery only; community-maintained metadata is not live fundamentals. |
| 3 | Calculations | FinanceToolkit | Transparent ratios and analytics using FMP/Yahoo or user-supplied statements. Provider lineage remains mandatory. |
| 4 | China/HK fallback | AKShare | Broad public-web adapter. Record the underlying website and retrieval time; expect endpoint drift. |

## Selection rules

- Resolve issuer identity before fetching financials. Keep primary listing, provider symbol, desk ticker and stable identifiers separate.
- Prefer official reported values to provider-standardized values. Retain both when standardization is analytically useful.
- Prefer consolidated statements unless the research question requires standalone accounts.
- Capture report status (`audited`, `unaudited`, `preliminary`, `restated` or `unknown`) and accounting basis.
- Never treat FinanceDatabase, FinanceToolkit or AKShare as the legal source of an official reported figure when the filing is available.
- Do not use the hosted FinanceToolkit MCP by default. A local optional package keeps credentials and inputs within the selected environment; hosted use requires a separate privacy and credential review.

## Credential variables

| Route | Environment variable |
| --- | --- |
| FinanceToolkit/FMP | `FINANCIAL_MODELING_PREP_API_KEY` (or `FMP_API_KEY`) |
| J-Quants | `JQUANTS_API_KEY` |
| OpenDART | `DART_API_KEY` |
| EdgarTools | `EDGAR_IDENTITY` |

Capability reporting exposes only whether each variable is configured, never its value.
