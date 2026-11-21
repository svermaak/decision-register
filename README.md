# Decision Register

A single source of truth for a project's decisions, facts, rules, open questions, actions, risks, assumptions and terms, with a knowledge base that agents can search.

**Status: specification only. No code has been written yet.**

- People read and edit the register in a portal.
- Agents read and write it through an API and an MCP server.
- A knowledge base (ChromaDB) indexes the register and outside sources such as policies and procedures.
- The register is published one way to Confluence.
- Every change makes a new version. Nothing is overwritten or deleted.
- Data is encrypted at rest. A copy is useless without the key.

Read the full design in [docs/spec.md](docs/spec.md).

## Planned stack

One Python app (API, portal and MCP server) with an encrypted SQLite database and ChromaDB inside it. It runs on your own machine with no admin rights, and as a Docker container on AWS or Azure.

## What must never be committed

No real project names, tenant IDs, web addresses, keys or register content. Settings come from environment values (see `.env.example`), and keys come from a secret store.

## Licence

MIT. See [LICENSE](LICENSE).
