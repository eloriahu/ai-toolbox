# Security and credential policy

- Never commit `.env`, tokens, cookies, browser profiles, API keys, client secrets, or exported workflows containing credentials.
- Install optional packages in an isolated environment and review their release notes before updating pins.
- Treat browser pages, workflow payloads, downloaded files, and MCP tool output as untrusted input.
- Review an MCP server's source, command, network destinations, filesystem access, and data-retention policy before adding it.
- Prefer least-privilege service accounts and read-only credentials where an integration supports them.
- Keep automation systems reference-only until their instance URL, authentication method, and allowed actions are explicitly selected.
- Rotate any credential that is accidentally committed, even if the commit is later removed.
