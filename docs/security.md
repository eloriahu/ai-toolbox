# Security and credential policy

- Never commit `.env`, tokens, cookies, browser profiles, API keys, client secrets, or exported workflows containing credentials.
- Install optional packages in an isolated environment and review their release notes before updating pins.
- Treat browser pages, workflow payloads, downloaded files, and MCP tool output as untrusted input.
- Review an MCP server's source, command, network destinations, filesystem access, and data-retention policy before adding it.
- Prefer least-privilege service accounts and read-only credentials where an integration supports them.
- Keep automation systems reference-only until their instance URL, authentication method, and allowed actions are explicitly selected.
- Prefer local optional finance packages when credentials or proprietary inputs are involved. Review data handling before using a hosted MCP or third-party proxy and do not send Bloomberg exports to one by default.
- Capability reports may state that an environment variable is configured but must never print, log or persist its value.
- Treat public-web adapters as unstable fallbacks. Preserve the underlying site, retrieval time and errors so a changed page cannot silently corrupt a model.
- Record each source's direct upstream origin and independence group. Syndicated copies and summaries must not be counted as separate confirmation.
- Idea funnels and research reviews are read-only. They must not produce or execute orders, change positions, infer personalized sizing or publish a report without separate authorization.
- Required report audits fail closed: missing critical fields, unverifiable lineage and zero successful verification block publication readiness.
- Rotate any credential that is accidentally committed, even if the commit is later removed.
