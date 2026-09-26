---
doc_type: feature
domain: api-knowledge-publication
stack: [Python 3.12+, FastAPI, Pydantic 2.x, SQLAlchemy 2.x, PostgreSQL]
node_id: "feature:api-knowledge-publication"
tags: [api, publication, environments, snapshots, ci-cd]
edges:
  - relation: implements
    target: "adr:architecture"
    read: must
  - relation: references
    target: "adr:api"
    read: must
  - relation: tested_by
    target: "adr:tests"
    read: must
  - relation: depends_on
    target: "feature:environment-snapshots"
    read: must
  - relation: depends_on
    target: "feature:snapshot-publication"
    read: optional
    when: "Read when changing snapshot construction, activation, idempotency, or publication persistence."
updated: 2026-09-26
---
# API Knowledge Publication

```graph
{"node_id":"feature:api-knowledge-publication","domain":"api-knowledge-publication","implements":["adr:architecture"],"tested_by":["adr:tests"],"entrypoints":["api/adapters/http/knowledge_publication_routes.py"],"registration_files":["api/server/app.py"],"reference_files":["api/adapters/http/api_security.py","core/application/knowledge_publication/use_cases/publish_knowledge/handler.py","core/infrastructure/postgres/repositories/knowledge_publication_repository.py","core/infrastructure/postgres/repositories/snapshot_payload_reader.py","core/infrastructure/postgres/repositories/snapshot_persistence_mapper.py","core/infrastructure/postgres/repositories/environment_repository.py"],"code_files":["core/application/knowledge_publication/ports/publication_baseline_reader.py","core/application/knowledge_publication/use_cases/get_publication_baseline.py","api/adapters/http/schemas/knowledge_publication_request.py","api/adapters/http/schemas/knowledge_publication_response.py","core/application/knowledge_publication/use_cases/publish_knowledge/inbound.py","core/application/knowledge_publication/use_cases/publish_knowledge/outbound.py","core/domain/knowledge_publication/aggregates/knowledge_publication.py","core/domain/knowledge_publication/types/publication_status.py","core/domain/knowledge_publication/value_objects/deployment_id.py","core/domain/knowledge_publication/value_objects/publication_id.py","core/infrastructure/postgres/models/knowledge_publication.py","core/infrastructure/postgres/models/environment.py","migrations/versions/001_foundation.py"],"test_files":["tests/unit/api/adapters/http/test_publication_baseline_routes.py","tests/unit/core/application/knowledge_publication/use_cases/test_document_graph.py","tests/integration/core/infrastructure/postgres/repositories/test_publication_baseline.py","tests/unit/core/infrastructure/postgres/repositories/test_snapshot_payload_reader.py","tests/unit/api/adapters/http/test_knowledge_publication_routes.py","tests/unit/api/adapters/http/test_api_authentication.py","tests/unit/core/application/knowledge_publication/use_cases/test_publish_knowledge.py","tests/unit/core/domain/knowledge_publication/test_knowledge_publication.py","tests/unit/core/infrastructure/postgres/repositories/test_knowledge_publication_repository.py"],"knowledge":{"schema_version":1,"entities":[{"id":"capability:publish-knowledge","type":"capability","label":"Publish knowledge snapshots","definition":"Accept complete deployment facts and activate them for a project environment.","aliases":[]},{"id":"rule:atomic-environment-activation","type":"rule","label":"Atomic environment activation","definition":"Persist snapshot facts, publication identity, and the current environment pointer in one transaction.","aliases":[]},{"id":"contract:deployment-publication","type":"contract","label":"Deployment publication","definition":"REST exchange for publishing a deployment snapshot with retry identity and an expected baseline.","aliases":[]}],"claims":[{"id":"claim:atomic-activation","subject":"capability:publish-knowledge","relation":"constrained_by","object":"rule:atomic-environment-activation","statement":"The repository locks the tenant-owned environment, writes normalized facts and publication identity, then changes current_snapshot_id in one transaction.","kind":"observation","status":"supported","evidence":[{"kind":"code","source":"core/infrastructure/postgres/repositories/knowledge_publication_repository.py","locator":"publish_atomically_with_environment: transaction, lock, inserts, pointer update","snapshot":null}],"derived_from":[],"gap":null},{"id":"claim:deployment-retry","subject":"capability:publish-knowledge","relation":"exposes","object":"contract:deployment-publication","statement":"A completed retry returns ALREADY_PUBLISHED only when its normalized payload hash matches; changed content raises RevisionConflict.","kind":"observation","status":"supported","evidence":[{"kind":"code","source":"core/application/knowledge_publication/use_cases/publish_knowledge/handler.py","locator":"PublishKnowledgeHandler.execute: completed retry hash comparison","snapshot":null}],"derived_from":[],"gap":null},{"id":"claim:environment-dependency","subject":"capability:publish-knowledge","relation":"depends_on","object":"feature:environment-snapshots#capability:track-environment-state","statement":"The handler builds ProjectKnowledgeSnapshot, then resolves and locks the selected environment before activation.","kind":"observation","status":"supported","evidence":[{"kind":"code","source":"core/application/knowledge_publication/use_cases/publish_knowledge/handler.py","locator":"PublishKnowledgeHandler._build_snapshot","snapshot":null},{"kind":"code","source":"core/infrastructure/postgres/repositories/knowledge_publication_repository.py","locator":"publish_atomically_with_environment: tenant environment lookup and lock","snapshot":null}],"derived_from":[],"gap":null}]}}
```

## PUBLICATION RULES

### Baseline read

Use `GET /v1/knowledge-publications/latest` with `memory:read` or `memory:publish` to load the environment's current snapshot, payload hash, facts, and SDK graph metadata.

REQUIRED: Query across tenants unless `tenant_id` is supplied; scope project/environment joins to that selected tenant when present. Return 404 for no baseline, 401/403 for denied authentication/authorization, and 422 for invalid parameters. Never treat access denial or server failure as permission to bootstrap.

### Graph-native documentation

The SDK publishes `adr`, `feature`, `document`, `document_revision`, and `document_section` entities. Keep complete ADR, feature, and digest Markdown in entity metadata; keep the generated graph index in snapshot metadata. The API still accepts its existing entity enum for other clients.

REQUIRED: Persist the graph index in `snapshots.metadata` and document facts in normalized entity/relation/evidence rows. Keep prior document versions in immutable snapshots and line revisions with Git merge conflict markers. Content and snapshot metadata changes participate in payload hashing and deployment-conflict checks. Migration `001` creates the final normalized fields without `snapshots.payload`; API details and SDK baselines reconstruct the existing payload shape from those rows.

### Activation

REQUIRED: Resolve project and environment inside the selected destination tenant.
REQUIRED: Accept body `tenant_id` from a token with `memory:publish`; otherwise default to its owner tenant. Admin publication requires a destination `tenant_id` in the body.
REQUIRED: Create a missing project/environment pair on its first trusted publication.
REQUIRED: Use `(tenant, project, environment, deployment_id)` as the idempotency lookup.
REQUIRED: Return the existing publication and snapshot for a completed retry.
REQUIRED: Under the environment lock, reject older ordered versions and a changed expected snapshot. Stage-only publication advances the project pointer only when it previously pointed to that environment's old snapshot.
REQUIRED: Allocate a distinct snapshot revision under the environment lock when another deployment already uses the version-derived revision. Hash the stored revision and compare retries against that revision.
REQUIRED: Use PostgreSQL `READ COMMITTED` for the locked revision allocation so a transaction waiting on the environment lock sees earlier commits.
REQUIRED: Create and promote the snapshot in one persistence operation.
REQUIRED: Preserve deployment ID, version, publication ID, and snapshot ID.
PROHIBITED: Treat a deployment as active before environment resolution succeeds.
PROHIBITED: Let callers mutate individual graph facts through this route.

## REFERENCES

- [**API.md**](../../adr/API.md): Defines API registration, versioning, and transport boundaries.
- [**TESTS.md**](../../adr/TESTS.md): Defines route and persistence verification tiers.
- [**environment-snapshots.md**](../core/environment-snapshots.md): Defines environment context and current snapshot behavior.
- [**snapshot-publication.md**](../core/snapshot-publication.md): Defines immutable snapshot and activation rules.
