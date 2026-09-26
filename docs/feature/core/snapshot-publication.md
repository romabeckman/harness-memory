---
doc_type: feature
domain: snapshot_publication
stack: [Python 3.12+, FastAPI, Pydantic 2.x, SQLAlchemy 2.x, PostgreSQL]
node_id: "feature:snapshot-publication"
tags: [snapshots, publication, idempotency, tenant]
edges:
  - relation: implements
    target: "adr:architecture"
  - relation: tested_by
    target: "adr:tests"
  - relation: references
    target: "adr:mcp"
  - relation: depends_on
    target: "feature:platform-foundation"
    read: must
updated: 2026-09-26
---
# Snapshot Publication
Publish a complete immutable project snapshot and switch its active pointer atomically.

```graph
{"node_id":"feature:snapshot-publication","domain":"snapshot_publication","implements":["adr:architecture"],"tested_by":["adr:tests"],"entrypoints":["api/adapters/http/knowledge_publication_routes.py"],"registration_files":["api/server/app.py"],"reference_files":["core/domain/snapshot_publication/aggregates/project_knowledge_snapshot.py","core/infrastructure/postgres/repositories/snapshot_publication_repository.py","core/infrastructure/postgres/repositories/snapshot_payload_reader.py"],"code_files":["harness_memory_mcp/services/tenant_context.py","harness_memory_mcp/services/publication_response_mapper.py","core/application/snapshot_publication/contracts/base.py","core/application/snapshot_publication/contracts/entity_input.py","core/application/snapshot_publication/contracts/evidence_input.py","core/application/snapshot_publication/contracts/project_input.py","core/application/snapshot_publication/contracts/relation_input.py","core/application/snapshot_publication/errors/missing_tenant_context.py","core/application/snapshot_publication/ports/snapshot_publication_store.py","core/application/snapshot_publication/services/canonical_payload_serializer.py","core/application/snapshot_publication/services/payload_hash_calculator.py","core/application/snapshot_publication/types/publication_context.py","core/application/snapshot_publication/types/publication_record.py","core/application/snapshot_publication/types/publication_status.py","core/application/snapshot_publication/services/snapshot_payload.py","core/application/snapshot_publication/use_cases/publish_project_snapshot/handler.py","core/application/snapshot_publication/use_cases/publish_project_snapshot/inbound.py","core/application/snapshot_publication/use_cases/publish_project_snapshot/outbound.py","core/domain/snapshot_publication/entities/entity_fact.py","core/domain/snapshot_publication/entities/evidence_fact.py","core/domain/snapshot_publication/entities/project_descriptor.py","core/domain/snapshot_publication/entities/relation_fact.py","core/domain/snapshot_publication/errors/persistence_failure.py","core/domain/snapshot_publication/errors/revision_conflict.py","core/domain/snapshot_publication/errors/snapshot_invariant_violation.py","core/domain/snapshot_publication/errors/stale_revision.py","core/domain/snapshot_publication/services/snapshot_builder.py","core/domain/snapshot_publication/services/snapshot_revision_policy.py","core/domain/snapshot_publication/types/entity_type.py","core/domain/snapshot_publication/types/provenance_kind.py","core/domain/snapshot_publication/types/relation_type.py","core/domain/snapshot_publication/types/revision_decision.py","core/domain/snapshot_publication/value_objects/current_snapshot_descriptor.py","core/domain/snapshot_publication/value_objects/entity_key.py","core/domain/snapshot_publication/value_objects/generated_at.py","core/domain/snapshot_publication/value_objects/metadata_object.py","core/domain/snapshot_publication/value_objects/payload_hash.py","core/domain/snapshot_publication/value_objects/project_descriptor.py","core/domain/snapshot_publication/value_objects/project_key.py","core/domain/snapshot_publication/value_objects/relation_reference.py","core/domain/snapshot_publication/value_objects/revision.py","core/domain/snapshot_publication/value_objects/schema_version.py","core/infrastructure/postgres/repositories/snapshot_graph_rows.py","core/infrastructure/postgres/repositories/snapshot_persistence_mapper.py","migrations/versions/011_snapshot_payload_removal.py"],"test_files":["tests/unit/core/application/snapshot_publication/contracts/test_inbound.py","tests/unit/core/application/snapshot_publication/helpers.py","tests/unit/core/application/snapshot_publication/services/test_payload_hash.py","tests/unit/core/application/snapshot_publication/use_cases/test_publish_project_snapshot.py","tests/unit/core/domain/snapshot_publication/services/test_revision_policy.py","tests/unit/core/domain/snapshot_publication/test_snapshot_domain.py","tests/unit/core/infrastructure/postgres/repositories/test_snapshot_persistence_mapper.py","tests/unit/core/infrastructure/postgres/repositories/test_snapshot_payload_reader.py","tests/unit/core/infrastructure/postgres/migrations/test_snapshot_payload_removal.py","tests/unit/core/infrastructure/postgres/test_snapshot_write_policy.py","tests/unit/mcp/services/test_publication_response_mapper.py","tests/integration/core/infrastructure/postgres/repositories/test_snapshot_publication_repository.py","tests/integration/core/infrastructure/postgres/repositories/test_publication_baseline.py","tests/unit/api/adapters/http/test_api_authentication.py"],"knowledge":{"schema_version":1,"entities":[{"id":"capability:publish-snapshot","type":"capability","label":"Publish knowledge snapshot","definition":"Validate and persist one immutable project knowledge snapshot.","aliases":[]},{"id":"rule:snapshot-reference-integrity","type":"rule","label":"Snapshot reference integrity","definition":"Require relation endpoints and evidence references to resolve within the published snapshot.","aliases":[]},{"id":"contract:snapshot-publication","type":"contract","label":"Snapshot publication","definition":"Accept a complete supported snapshot and return its publication status and snapshot identity.","aliases":[]}],"claims":[{"id":"claim:snapshot-reference-validation","subject":"capability:publish-snapshot","relation":"constrained_by","object":"rule:snapshot-reference-integrity","statement":"ProjectKnowledgeSnapshot validates publication facts before persistence, including references scoped to the same snapshot.","kind":"observation","status":"supported","evidence":[{"kind":"code","source":"core/domain/snapshot_publication/aggregates/project_knowledge_snapshot.py","locator":"ProjectKnowledgeSnapshot._validate","snapshot":null}],"derived_from":[],"gap":null},{"id":"claim:atomic-snapshot-persistence","subject":"capability:publish-snapshot","relation":"exposes","object":"contract:snapshot-publication","statement":"The PostgreSQL repository atomically persists normalized facts and returns publication status, with bounded transient retries.","kind":"observation","status":"supported","evidence":[{"kind":"code","source":"core/infrastructure/postgres/repositories/snapshot_publication_repository.py","locator":"PostgresSnapshotPublicationRepository.publish_atomically and _publish_once","snapshot":null}],"derived_from":[],"gap":null}]}}
```

## OVERVIEW

Validate a complete schema `1.0` payload, build an immutable domain aggregate, calculate a canonical hash, and persist the graph through a tenant-scoped transaction.

## FOLDER STRUCTURE

- `core/{domain,application,infrastructure/postgres}/`: snapshot invariants, publication, and persistence; `api/adapters/http/`: authenticated write boundary.

## MAIN CONCEPTS / COMPONENTS

- **Complete snapshot**: Validate same-snapshot references; derive tenant from trusted `PublicationContext`.
- **Revision policy**: Activate higher revisions; return `ALREADY_PUBLISHED` for matching revision/hash; reject stale or conflicting revisions.
- **Persistence**: Switch `projects.active_snapshot_id`; retain history and reconstruct REST/SDK payloads from normalized rows.

## HOW TO PUBLISH

1. Submit schema `1.0`, positive revision, offset-aware timestamp, and bounded facts.
2. Resolve tenant from trusted context; treat `ACTIVATED` as new state and `ALREADY_PUBLISHED` as an idempotent retry.
3. Retry transient uniqueness, serialization, or deadlock races within the configured bound.

## PERSISTENCE AND MCP CONTINUITY

Store document content in normalized `entities.metadata`; REST details and SDK baselines reconstruct payloads from entity, relation, and evidence rows. Migration `011` verifies stored payloads before dropping `snapshots.payload` and aborts on mismatches.

## PARAMETERS / CONFIGURATIONS

| Field | Contract |
|-------|----------|
| `schema_version` | `1.0` |
| `revision` | Positive integer. |
| `generated_at` | Offset-aware timestamp normalized to UTC. |
| `entities` | Up to 10,000 facts. |
| `relations`, `evidence` | Up to 50,000 facts each. |

## BEST PRACTICES

REQUIRED: Hash validated canonical facts and revision while excluding generated timestamps and tenant context.
REQUIRED: Keep Pydantic shape validation separate from domain graph invariants.
REQUIRED: Map persistence failures to stable API errors without SQL, credentials, or payload contents.
REQUIRED: Keep API publication authorization failures separate from graph invariant and persistence failures.
PROHIBITED: Expose publication through MCP.
PROHIBITED: Delete historical snapshots when activating a newer revision.
PROHIBITED: Allow arbitrary graph mutations outside complete snapshot publication.

## REFERENCES

- [**ARCHITECTURE.md**](../../adr/ARCHITECTURE.md): Defines dependency direction and persistence ownership.
- [**TESTS.md**](../../adr/TESTS.md): Defines domain, persistence, and MCP test boundaries.
- [**MCP.md**](../../adr/MCP.md): Defines the tool and trusted-context boundary.
- [**platform-foundation.md**](./platform-foundation.md): Supplies schema, engine, and migration foundations.
