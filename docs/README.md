# Project Documentation

Index of project technical documentation for **harness-memory**. Use the links below to navigate the available documents and graph map topology.

## Documentation Index

| Document | Description | Reading |
|----------|-------------|----------|
| [**.digest.md**](./.digest.md) | Fast-path machine-readable orientation digest for stack, commands, and constraints. | **Mandatory** |
| [**.graph.json**](./.graph.json) | Macro relation graph index for document topology and 1-hop routing. | **Mandatory** |
| [**ARCHITECTURE.md**](./adr/ARCHITECTURE.md) | Global architecture, module map, and dependency rules for the project. | **Mandatory** |
| [**API.md**](./adr/API.md) | FastAPI architecture, shared persistence boundary, and token handoff to MCP. | Optional |
| [**TESTS.md**](./adr/TESTS.md) | Testing strategies, patterns, and execution commands. | **Mandatory** |
| [**MCP.md**](./adr/MCP.md) | MCP tools, resources, prompts, contracts, and security boundaries. | Optional |
| [**users-and-tokens.md**](./feature/api/users-and-tokens.md) | FastAPI user and MCP-token CRUD contract. | Optional |
| [**mcp-access-surface.md**](./feature/mcp/mcp-access-surface.md) | MCP resources and deterministic workflow prompts. | Optional |
| [**tenant-security.md**](./feature/mcp/tenant-security.md) | MCP tenant isolation, scopes, and security audit behavior. | Optional |
| [**token-authentication.md**](./feature/mcp/token-authentication.md) | API-issued bearer-token authentication for MCP clients. | Optional |
| [**platform-foundation.md**](./feature/core/platform-foundation.md) | Shared PostgreSQL foundation, migrations, and platform runtime. | Optional |
| [**snapshot-publication.md**](./feature/core/snapshot-publication.md) | Versioned knowledge snapshot publication and activation. | Optional |
| [**entity-discovery.md**](./feature/core/entity-discovery.md) | Bounded entity discovery from the active snapshot. | Optional |
| [**relationship-context.md**](./feature/core/relationship-context.md) | Bounded relationship context and dependency queries. | Optional |
| [**integration-paths.md**](./feature/core/integration-paths.md) | Bounded integration path discovery. | Optional |
| [**impact-analysis.md**](./feature/core/impact-analysis.md) | Structured change-impact analysis. | Optional |
| [**production-delivery.md**](./feature/core/production-delivery.md) | Project-wide containers, startup safety, CI, and telemetry. | Optional |
| [**PLAYBOOK-DAILY-USE.md**](./workflow/PLAYBOOK-DAILY-USE.md) | Practical daily workflow for developers using Harness Memory through MCP clients. | Optional |

## Recommended Reading Order

If an exact path is supplied, read that target directly. Otherwise use this order:

1. **.digest.md** — fast AI orientation for architecture pattern, stack, and test commands.
2. **.graph.json** — macro document graph for one-hop routing.
3. **ARCHITECTURE.md** — global modules and dependency boundaries.
4. **TESTS.md** — test strategy and coverage requirements.
5. Read **API.md** or **MCP.md** for the selected interface, then the related `feature/api/`, `feature/mcp/`, or `feature/core/` document.
