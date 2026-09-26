---
doc_type: feature
domain: snapshot_publisher
stack: [TypeScript 7.x, Node.js 20+, Vitest 4.x, Git, REST, JSON Schema]
node_id: "feature:snapshot-publisher"
tags: [sdk, cli, publication, pipeline, snapshots]
edges:
  - relation: implements
    target: "adr:architecture"
  - relation: tested_by
    target: "adr:tests"
  - relation: depends_on
    target: "feature:api-knowledge-publication"
  - relation: references
    target: "feature:environment-snapshots"
  - relation: references
    target: "adr:security"
updated: 2026-09-26
---
# Snapshot Publisher SDK
Collect, validate, and publish repository knowledge through REST.

```graph
{"node_id":"feature:snapshot-publisher","domain":"snapshot_publisher","implements":["adr:architecture"],"tested_by":["adr:tests"],"entrypoints":["sdk/src/cli/index.ts","sdk/src/index.ts"],"registration_files":["sdk/package.json","sdk/src/cli/cli-app.ts","sdk/src/infrastructure/llm/agent-runner-factory.ts"],"reference_files":["sdk/src/application/publish-snapshot/publish-snapshot.use-case.ts","sdk/src/application/publish-snapshot/phases/abstract-publication-phase.ts","sdk/src/infrastructure/api/rest-publication-client.ts","sdk/src/infrastructure/validator/graph-validator.ts"],"code_files":["sdk/src/application/publish-snapshot/phases/validate-options-phase.ts","sdk/src/application/publish-snapshot/phases/validate-publication-target-phase.ts","sdk/src/application/publish-snapshot/phases/collect-context-phase.ts","sdk/src/application/publish-snapshot/phases/generate-with-docs-phase.ts","sdk/src/application/publish-snapshot/phases/route-documentation-phase.ts","sdk/src/application/publish-snapshot/phases/validate-graph-phase.ts","sdk/src/application/publish-snapshot/phases/publish-phase.ts","sdk/src/application/memory/project-memory-workflow.ts","sdk/src/application/memory/project-memory-completeness.ts","sdk/src/application/memory/project-memory-prompt.ts","sdk/src/application/memory/memory-graph.ts","sdk/src/application/memory/memory-document-validator.ts","sdk/src/application/memory/document-content-codec.ts","sdk/src/application/ports/docs-store.port.ts","sdk/src/application/ports/documentation-directory.port.ts","sdk/src/application/ports/memory-workflow.port.ts","sdk/src/application/ports/publication-baseline.port.ts","sdk/src/infrastructure/memory/local-docs-store.ts","sdk/src/infrastructure/memory/local-docs-directory.ts","sdk/src/infrastructure/api/publication-baseline-client.ts","sdk/src/application/ports/llm-runner.port.ts","sdk/src/application/ports/publication-client.port.ts","sdk/src/domain/contracts.ts","sdk/src/domain/llm-agent.ts","sdk/src/infrastructure/config/config-resolver.ts","sdk/src/infrastructure/git/git-context-collector.ts","sdk/src/infrastructure/llm/llm-agent-runner.ts","sdk/src/infrastructure/llm/codex-cli-runner.ts","sdk/src/infrastructure/llm/claude-cli-runner.ts","sdk/src/infrastructure/llm/antigravity-cli-runner.ts","sdk/src/infrastructure/llm/copilot-cli-runner.ts","sdk/src/infrastructure/llm/local-llm-runner.ts"],"test_files":["sdk/tests/unit/application/publish-snapshot/publish-snapshot-phases.test.ts","sdk/tests/unit/application/memory/memory-graph.test.ts","sdk/tests/unit/application/memory/memory-document-validator.test.ts","sdk/tests/unit/application/memory/project-memory-workflow.test.ts","sdk/tests/integration/infrastructure/memory/local-docs-store.test.ts","sdk/tests/unit/infrastructure/api/rest-publication-client.test.ts","sdk/tests/unit/infrastructure/llm/local-llm-runner.test.ts","sdk/tests/unit/infrastructure/validator/graph-validator.test.ts","sdk/tests/integration/http-publication-boundary.test.ts","sdk/tests/e2e/cli-publish.test.ts"],"knowledge":{"schema_version":1,"entities":[{"id":"contract:temporary-llm-graph-output","type":"contract","label":"Temporary LLM graph output","definition":"Per-invocation temporary JSON file requested for generated graph output.","aliases":[]},{"id":"rule:temporary-output-cleanup","type":"rule","label":"Temporary output cleanup","definition":"Remove the invocation's temporary output directory after the LLM process ends.","aliases":[]},{"id":"capability:publish-snapshots","type":"capability","label":"Publish snapshots","definition":"Collect repository docs, validate a graph, and publish it through REST.","aliases":[]},{"id":"rule:validate-before-publish","type":"rule","label":"Validate before publish","definition":"Preflight the live target and validate the graph before publication.","aliases":[]},{"id":"contract:sdk-publication","type":"contract","label":"SDK publication","definition":"Publish a validated graph with deployment identity and an expected snapshot baseline.","aliases":[]}],"claims":[{"id":"claim:llm-graph-file-contract","subject":"contract:temporary-llm-graph-output","relation":null,"object":null,"statement":"Prompt the selected CLI with an absolute per-run graph-output.json path; read it when present and fall back to stdout when absent.","kind":"observation","status":"supported","evidence":[{"kind":"code","source":"sdk/src/infrastructure/llm/local-llm-runner.ts","locator":"LocalLlmRunner.run, runWithTemporaryOutput, readTemporaryGraph","snapshot":null},{"kind":"test_definition","source":"sdk/tests/unit/infrastructure/llm/local-llm-runner.test.ts","locator":"reads the graph from the prompted temporary JSON file when stdout has no graph; runs node script as fake llm and parses json stdout","snapshot":null}],"derived_from":[],"gap":null},{"id":"claim:temporary-output-cleanup","subject":"rule:temporary-output-cleanup","relation":null,"object":null,"statement":"Remove the temporary output directory after child-process success or failure.","kind":"observation","status":"supported","evidence":[{"kind":"code","source":"sdk/src/infrastructure/llm/local-llm-runner.ts","locator":"LocalLlmRunner.run finally block","snapshot":null},{"kind":"test_definition","source":"sdk/tests/unit/infrastructure/llm/local-llm-runner.test.ts","locator":"reads the graph from the prompted temporary JSON file when stdout has no graph; asserts file and directory removal","snapshot":null}],"derived_from":[],"gap":null},{"id":"claim:provider-file-write-compatibility","subject":"contract:temporary-llm-graph-output","relation":null,"object":null,"statement":"Provider CLIs can write the requested file under their actual permission settings.","kind":"hypothesis","status":"unresolved","evidence":[{"kind":"test_definition","source":"sdk/tests/unit/infrastructure/llm/local-llm-runner.test.ts","locator":"temporary-file response is simulated by a Node child process; provider CLI permissions are not exercised","snapshot":null}],"derived_from":[],"gap":"Run integration checks with each installed Codex, Claude, Antigravity, and Copilot CLI."},{"id":"claim:sdk-preflight-and-validation","subject":"capability:publish-snapshots","relation":"constrained_by","object":"rule:validate-before-publish","statement":"Preflight live targets before collection and validate graphs before publishing; dry runs skip target preflight.","kind":"observation","status":"supported","evidence":[{"kind":"code","source":"sdk/src/application/publish-snapshot/publish-snapshot.use-case.ts","locator":"PublishSnapshotUseCase.execute","snapshot":null},{"kind":"code","source":"sdk/src/application/publish-snapshot/phases/validate-graph-phase.ts","locator":"ValidateGraphPhase.execute","snapshot":null}],"derived_from":[],"gap":null},{"id":"claim:sdk-baseline-publication","subject":"capability:publish-snapshots","relation":"exposes","object":"contract:sdk-publication","statement":"Return NO_CHANGES only when ADR/feature text and publishable content plus metadata match baseline; otherwise publish the validated graph with tenant and expected snapshot ID.","kind":"observation","status":"supported","evidence":[{"kind":"code","source":"sdk/src/application/publish-snapshot/phases/publish-phase.ts","locator":"PublishPhase.execute","snapshot":null},{"kind":"code","source":"sdk/src/application/memory/project-memory-workflow.ts","locator":"ProjectMemoryWorkflow.run: unchanged-document and baseline comparison branches","snapshot":null}],"derived_from":[],"gap":null}]}}
```

## OVERVIEW

Collect Git context and publish validated graphs.


## PUBLISHING FLOW

1. Validate options; preflight live targets before collection. Dry runs skip preflight.
2. Require complete docs; synthesize on ADR/feature changes; reconcile other docs without the model.
3. Collect bounded Git context; retain `docs/`, honor `--exclude-paths`, validate Schema 1.0, canonicalize keys, and hash.
4. Publish through REST with an expected baseline; retry 429/5xx with jitter.

## LLM AND SECURITY RULES

REQUIRED: Default to `HARNESS_MEMORY_API_KEY`; allow alternatives through `--token-env` or programmatic `token`. Reject `--tenant` and `--token` with exit code 2.
REQUIRED: Sanitize child environments, keep repository symlinks, honor stdin backpressure, and use per-run temporary directories. Accept only regular JSON output up to 50 MiB; remove each directory after the child exits.
REQUIRED: Support `codex-cli`, `claude-cli`, `antigravity-cli`, and `copilot-cli`; keep Antigravity `--dangerously-skip-permissions` and Copilot `--allow-all --autopilot`; cap Copilot Windows prompts at 30,000 and Codex input at 1,048,576 characters.
PROHIBITED: Publish through MCP or retry HTTP 400, 401, 403, or 409 responses.


## REFERENCES

- [**ARCHITECTURE.md**](../../adr/ARCHITECTURE.md): Architecture.
- [**TESTS.md**](../../adr/TESTS.md): Test policy.
- [**knowledge-publication.md**](../api/knowledge-publication.md): REST boundary.
- [**environment-snapshots.md**](../core/environment-snapshots.md): Environment lifecycle.
- [**SECURITY.md**](../../adr/SECURITY.md): Security controls.
