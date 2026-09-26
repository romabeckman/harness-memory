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
Collect repository context, validate graphs, and publish snapshots through REST.

```graph
{"node_id":"feature:snapshot-publisher","domain":"snapshot_publisher","implements":["adr:architecture"],"tested_by":["adr:tests"],"entrypoints":["sdk/src/cli/index.ts","sdk/src/index.ts"],"registration_files":["sdk/package.json","sdk/src/cli/cli-app.ts","sdk/src/infrastructure/llm/agent-runner-factory.ts"],"reference_files":["sdk/src/application/publish-snapshot/publish-snapshot.use-case.ts","sdk/src/application/publish-snapshot/phases/abstract-publication-phase.ts","sdk/src/infrastructure/api/rest-publication-client.ts","sdk/src/infrastructure/validator/graph-validator.ts"],"code_files":["sdk/src/application/publish-snapshot/phases/validate-options-phase.ts","sdk/src/application/publish-snapshot/phases/validate-graph-phase.ts","sdk/src/application/publish-snapshot/phases/publish-phase.ts","sdk/src/application/memory/project-memory-workflow.ts","sdk/src/application/ports/llm-runner.port.ts","sdk/src/domain/llm-agent.ts","sdk/src/infrastructure/config/config-resolver.ts","sdk/src/infrastructure/llm/llm-agent-runner.ts","sdk/src/infrastructure/llm/codex-cli-runner.ts","sdk/src/infrastructure/llm/claude-cli-runner.ts","sdk/src/infrastructure/llm/antigravity-cli-runner.ts","sdk/src/infrastructure/llm/copilot-cli-runner.ts","sdk/src/infrastructure/llm/agy-cli-runner.ts","sdk/src/infrastructure/llm/local-llm-runner.ts"],"test_files":["sdk/tests/unit/infrastructure/config/config-resolver.test.ts","sdk/tests/unit/infrastructure/llm/agent-runner-factory.test.ts","sdk/tests/unit/infrastructure/llm/codex-cli-runner.test.ts","sdk/tests/unit/infrastructure/llm/claude-cli-runner.test.ts","sdk/tests/unit/infrastructure/llm/antigravity-cli-runner.test.ts","sdk/tests/unit/infrastructure/llm/copilot-cli-runner.test.ts","sdk/tests/unit/infrastructure/llm/agy-cli-runner.test.ts","sdk/tests/unit/infrastructure/llm/local-llm-runner.test.ts","sdk/tests/integration/child-process-llm.test.ts"],"knowledge":{"schema_version":1,"entities":[{"id":"contract:temporary-llm-graph-output","type":"contract","label":"Temporary LLM graph output","definition":"Per-invocation JSON file requested for generated graph output.","aliases":[]},{"id":"rule:temporary-output-cleanup","type":"rule","label":"Temporary output cleanup","definition":"Remove the invocation's temporary output directory after the LLM process ends.","aliases":[]},{"id":"capability:publish-snapshots","type":"capability","label":"Publish snapshots","definition":"Collect repository docs, validate a graph, and publish it through REST.","aliases":[]},{"id":"rule:validate-before-publish","type":"rule","label":"Validate before publish","definition":"Preflight live targets and validate graphs before publication.","aliases":[]},{"id":"contract:sdk-publication","type":"contract","label":"SDK publication","definition":"Publish a validated graph with deployment identity and an expected snapshot baseline.","aliases":[]},{"id":"contract:llm-prompt-transport","type":"contract","label":"LLM prompt transport","definition":"Pass generated repository context to the selected local LLM process.","aliases":[]}],"claims":[{"id":"claim:llm-graph-file-contract","subject":"contract:temporary-llm-graph-output","relation":null,"object":null,"statement":"Prompt the selected CLI with an absolute per-run graph-output.json path; read it when present and fall back to stdout when absent.","kind":"observation","status":"supported","evidence":[{"kind":"code","source":"sdk/src/infrastructure/llm/local-llm-runner.ts","locator":"LocalLlmRunner.run, runWithTemporaryOutput, readTemporaryGraph","snapshot":null},{"kind":"test_definition","source":"sdk/tests/unit/infrastructure/llm/local-llm-runner.test.ts","locator":"temporary JSON output and stdout fallback cases","snapshot":null}],"derived_from":[],"gap":null},{"id":"claim:temporary-output-cleanup","subject":"rule:temporary-output-cleanup","relation":null,"object":null,"statement":"Remove the temporary output directory after child-process success or failure.","kind":"observation","status":"supported","evidence":[{"kind":"code","source":"sdk/src/infrastructure/llm/local-llm-runner.ts","locator":"LocalLlmRunner.run finally block","snapshot":null},{"kind":"test_definition","source":"sdk/tests/unit/infrastructure/llm/local-llm-runner.test.ts","locator":"asserts output file and directory removal","snapshot":null}],"derived_from":[],"gap":null},{"id":"claim:provider-file-write-compatibility","subject":"contract:temporary-llm-graph-output","relation":null,"object":null,"statement":"Supported provider CLIs can write the requested file under their actual permission settings.","kind":"hypothesis","status":"unresolved","evidence":[{"kind":"test_definition","source":"sdk/tests/unit/infrastructure/llm/local-llm-runner.test.ts","locator":"temporary-file response is simulated by a Node child process","snapshot":null}],"derived_from":[],"gap":"Run integration checks with installed Codex, Claude, Antigravity, Copilot, and AGY CLIs."},{"id":"claim:sdk-preflight-and-validation","subject":"capability:publish-snapshots","relation":"constrained_by","object":"rule:validate-before-publish","statement":"Preflight live targets before collection and validate graphs before publishing; dry runs skip target preflight.","kind":"observation","status":"supported","evidence":[{"kind":"code","source":"sdk/src/application/publish-snapshot/publish-snapshot.use-case.ts","locator":"PublishSnapshotUseCase.execute","snapshot":null},{"kind":"code","source":"sdk/src/application/publish-snapshot/phases/validate-graph-phase.ts","locator":"ValidateGraphPhase.execute","snapshot":null}],"derived_from":[],"gap":null},{"id":"claim:sdk-baseline-publication","subject":"capability:publish-snapshots","relation":"exposes","object":"contract:sdk-publication","statement":"Return NO_CHANGES only when ADR/feature text and publishable graph content plus metadata match baseline; otherwise publish with tenant and expected snapshot ID.","kind":"observation","status":"supported","evidence":[{"kind":"code","source":"sdk/src/application/publish-snapshot/phases/publish-phase.ts","locator":"PublishPhase.execute","snapshot":null},{"kind":"code","source":"sdk/src/application/memory/project-memory-workflow.ts","locator":"unchanged-document and baseline comparison branches","snapshot":null}],"derived_from":[],"gap":null},{"id":"claim:runner-prompt-transport","subject":"capability:publish-snapshots","relation":"exposes","object":"contract:llm-prompt-transport","statement":"Use argument transport when a runner configures it; otherwise stream JSON context to stdin with backpressure.","kind":"observation","status":"supported","evidence":[{"kind":"code","source":"sdk/src/infrastructure/llm/local-llm-runner.ts","locator":"prompt construction and inputWrite branch","snapshot":null},{"kind":"code","source":"sdk/src/infrastructure/llm/copilot-cli-runner.ts","locator":"promptTransport = argument","snapshot":null},{"kind":"test_definition","source":"sdk/tests/unit/infrastructure/llm/local-llm-runner.test.ts","locator":"passes complete context as Copilot prompt argument","snapshot":null}],"derived_from":[],"gap":null}]}}
```

## PUBLISHING FLOW

1. Validate target, credentials, agent, and deployment identity; resolve a memory:publish token.
2. For live runs, preflight project, environment, and deployment before Git collection. Reject ambiguous targets; allow a new environment.
3. Collect bounded context. Synthesize when ADR or feature text changes; reconcile other docs without model execution.
4. Validate the graph and compare baseline text plus publishable content and metadata. Return NO_CHANGES only when unchanged; otherwise publish with expected snapshot ID.

## LLM ADAPTERS AND SAFETY

Use separate runners for codex-cli, claude-cli, antigravity-cli, copilot-cli, and agy-cli. Copilot sends prompts as arguments; other runners use stdin. Read per-run JSON output or fall back to stdout.

REQUIRED: Strip token, key, secret, password, and auth variables from child environments. Use a unique temporary directory and remove it after process success or failure.
REQUIRED: Accept regular JSON files only. Limit output to 50 MiB, Codex input to 1,048,576 characters, and Windows argument prompts to 30,000 characters.
REQUIRED: Retry timeouts and HTTP 408, 429, or 5xx with bounded backoff; do not retry authorization, validation, or conflict responses.
PROHIBITED: Publish through MCP; accept raw --tenant or --token options.

## CONFIGURATION

| Option | Environment variable | Use |
|---|---|---|
| --agent | HARNESS_MEMORY_AGENT | Required runner ID. |
| --tenant-id | HARNESS_MEMORY_TENANT_ID | Select tenant for ambiguous project keys. |
| --token-env | HARNESS_MEMORY_TOKEN_ENV | Token variable; defaults to HARNESS_MEMORY_API_KEY. |
| --dry-run | HARNESS_MEMORY_DRY_RUN | Skip target preflight and publication. |

## DOCUMENT HISTORY

Persist docs as entities, relations, and evidence with path, content, checksum, commit, and change state; retain removed revisions.

## REFERENCES

- [**ARCHITECTURE.md**](../../adr/ARCHITECTURE.md): SDK boundary.
- [**TESTS.md**](../../adr/TESTS.md): Test tiers.
- [**knowledge-publication.md**](../api/knowledge-publication.md): REST contract.
- [**environment-snapshots.md**](../core/environment-snapshots.md): Snapshot lifecycle.
- [**SECURITY.md**](../../adr/SECURITY.md): Token scopes.
