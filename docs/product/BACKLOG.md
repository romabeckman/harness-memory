| ID | Title | Domain | Agent | Priority | Dependencies | Reworks | Score (TL) | Score (Adv) | Status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| F001 | Publish immutable project snapshots with graph endpoint invariant checks and idempotent retries that preserve the active revision | snapshot_publication | backend | CRITICAL | None | 0 | - | - | COMPLETED |
| F002 | Search tenant active snapshots by exact key, literal case-insensitive name prefix, type, or project with deterministic bounded pagination and stable validation errors | entity_discovery | backend | CRITICAL | F001 | 0 | - | - | COMPLETED |
| F003 | Return bounded entity context and inbound or outbound dependencies with active-snapshot scoping, evidence limits, direction validation, and safe not-found responses | relationship_context | backend | CRITICAL | F002 | 0 | - | - | COMPLETED |
| F004 | Find tenant-scoped direct, zero-hop, and multi-hop integration paths with strict traversal bounds, deterministic termination data, and safe endpoint errors | integration_paths | backend | HIGH | F003 | 0 | - | - | COMPLETED |
| F005 | Analyze structured change impact with bounded direct and indirect consumers, truncation metadata, target validation, and serialized response budgets | impact_analysis | backend | HIGH | F004 | 0 | - | - | COMPLETED |
| F006 | Enforce MCP bearer authentication and tenant isolation, reject payload tenant overrides, and return stable unauthorized and validation errors | mcp_tenant_security | backend | CRITICAL | F001, F002, F003, F004, F005 | 0 | - | - | COMPLETED |
