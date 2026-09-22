# Harness Memory SDK

The Harness Memory SDK is a TypeScript library and CLI for publishing a repository's environment knowledge to Harness Memory from a CI/CD pipeline.

It performs this pipeline:

```text
Git repository
  -> tracked source files and optional diff
  -> local LLM graph synthesis
  -> schema validation and canonical SHA-256
  -> REST publication at /v1/knowledge-publications
```

The SDK is the deterministic publication client. MCP is the read-only interface for querying the knowledge graph. Do not publish through MCP.

## Prerequisites

- Node.js 20 or newer.
- npm.
- A Git repository.
- A local LLM command. The default command is `codex`.
- A running Harness Memory API for a real publication.
- An active tenant-bound service-account token with the exact `memory:publish` scope.

For local development, start the API from the repository root with Docker Compose:

```bash
export API_ADMIN_TOKEN='replace-with-a-high-entropy-admin-secret'
docker compose up --build -d
```

Use the [API guide](../api/README.md) to create a service account and issue its publication token. The API admin token manages credentials; it is not a publication token.

## Install and build

From the repository root:

```bash
npm --prefix sdk ci
npm --prefix sdk run build
```

Or from `sdk/`:

```bash
npm ci
npm run build
```

The compiled CLI is `sdk/dist/cli/index.js`. To use the command name locally after building:

```bash
cd sdk
npm link
cd ..
harness-memory publish \
  --model gpt-5 \
  --effort medium \
  --environment staging \
  --project-key payments \
  --deployment-id premerge-123 \
  --version v1.2.3 \
  --dry-run
```

## Quick start

Set the publication token in the environment. Never put it in a command argument, config file, source file, or log.

```bash
export HARNESS_MEMORY_API_TOKEN='replace-with-service-account-token'

node sdk/dist/cli/index.js publish \
  --model gpt-5 \
  --effort high \
  --environment production \
  --project-key payments \
  --deployment-id deploy-123 \
  --version v1.2.3 \
  --api-url http://localhost:8080 \
  --verbose
```

`publish` is optional. These forms are equivalent:

```bash
node sdk/dist/cli/index.js publish <options>
node sdk/dist/cli/index.js <options>
```

`--api-url` is the API origin, such as `https://memory.example.com` or `http://localhost:8080`. The client always appends `/v1/knowledge-publications`.

## Dry run

Use dry run in pull-request or pre-merge validation. It collects the repository, runs the LLM, validates the graph, computes its SHA-256, and skips the API request.

```bash
node sdk/dist/cli/index.js publish \
  --model gpt-5 \
  --effort medium \
  --environment staging \
  --project-key payments \
  --deployment-id premerge-123 \
  --version "$GITHUB_SHA" \
  --dry-run \
  --output text \
  --verbose
```

Dry run still requires `model`, `effort`, `environment`, `project-key`, `deployment-id`, and `version`. It does not require `api-url` or a token.

## Configuration

Configuration can come from, in descending precedence:

1. CLI flags.
2. Environment variables.
3. A JSON file.
4. Built-in defaults and CI metadata fallbacks.

The default file is `.harness-memory.json` in the current directory. Select another file with `--config path/to/config.json` or `HARNESS_MEMORY_CONFIG`.

Example `.harness-memory.json`:

```json
{
  "agent": "codex-cli",
  "model": "gpt-5",
  "effort": "high",
  "environment": "production",
  "projectKey": "payments",
  "deploymentId": "deploy-123",
  "version": "v1.2.3",
  "apiUrl": "https://memory.example.com",
  "tokenEnv": "HARNESS_MEMORY_API_TOKEN",
  "repository": ".",
  "baseRef": "origin/main",
  "headRef": "HEAD",
  "timeout": 600,
  "maxFiles": 2000,
  "maxBytes": 10485760,
  "dryRun": false,
  "verbose": false
}
```

Config-file properties use camelCase. The token is always read from the environment variable named by `tokenEnv`; the file cannot contain the token. `output` is controlled by `--output` or `HARNESS_MEMORY_OUTPUT`, not by this file.

When values are absent, the resolver uses these fallbacks:

- `deployment-id`: `CI_PIPELINE_ID`, `GITHUB_RUN_ID`, `BUILD_ID`, then `CI_JOB_ID`.
- `version`: `CI_COMMIT_SHA`, `GITHUB_SHA`, then `GIT_COMMIT`.
- `base-ref`: `CI_MERGE_REQUEST_DIFF_BASE_SHA`, then `GITHUB_BASE_REF`.
- `head-ref`: `HEAD`.
- `llm-command`: `codex`.
- `token-env`: `HARNESS_MEMORY_API_TOKEN`.
- `timeout`: 600 seconds.
- `max-files`: 2,000.
- `max-bytes`: 10,485,760 bytes.
- Output: JSON in CI, text outside CI.

## CLI options

| Flag | Environment variable | Required | Description |
| --- | --- | --- | --- |
| `--agent` | `HARNESS_MEMORY_AGENT` | No | Runner: `codex-cli` or `claude-cli`. Default: `codex-cli`. |
| `--model` | `HARNESS_MEMORY_MODEL` | Yes | Model passed to the selected runner. |
| `--effort` | `HARNESS_MEMORY_EFFORT` | Yes | `low`, `medium`, `high`, or `xhigh`. |
| `--environment` | `HARNESS_MEMORY_ENVIRONMENT` | Yes | Target environment, for example `production`. |
| `--project-key` | `HARNESS_MEMORY_PROJECT_KEY` | Yes | Stable project identifier. |
| `--deployment-id` | `HARNESS_MEMORY_DEPLOYMENT_ID` | Yes | CI deployment execution identifier. |
| `--version` | `HARNESS_MEMORY_VERSION` | Yes | Release version or commit identifier. |
| `--api-url` | `HARNESS_MEMORY_API_URL` | Real publish only | API origin. |
| `--token-env` | `HARNESS_MEMORY_TOKEN_ENV` | No | Environment variable containing token. Default: `HARNESS_MEMORY_API_TOKEN`. |
| `--repository` | `HARNESS_MEMORY_REPOSITORY` | No | Repository path. Default: `.`. |
| `--base-ref` | `HARNESS_MEMORY_BASE_REF` | No | Git ref used to calculate the diff. |
| `--head-ref` | `HARNESS_MEMORY_HEAD_REF` | No | Git ref to publish. Default: `HEAD`. |
| `--llm-command` | `HARNESS_MEMORY_LLM_COMMAND` | No | Executable override for the selected runner. |
| `--config` | `HARNESS_MEMORY_CONFIG` | No | JSON configuration path. |
| `--timeout` | `HARNESS_MEMORY_TIMEOUT` | No | LLM timeout in seconds, from 1 to 3,600. |
| `--max-files` | `HARNESS_MEMORY_MAX_FILES` | No | Maximum tracked files loaded into context. |
| `--max-bytes` | `HARNESS_MEMORY_MAX_BYTES` | No | Maximum context bytes loaded into memory. |
| `--dry-run` | `HARNESS_MEMORY_DRY_RUN` | No | Validate without publishing. |
| `--output` | `HARNESS_MEMORY_OUTPUT` | No | `json` or `text`. |
| `--verbose` | `HARNESS_MEMORY_VERBOSE` | No | Print progress information to stderr. |

Boolean flags are passed without a value:

```bash
--dry-run --verbose
```

## CI/CD example

The publication step is independent of the CI provider. The pipeline must provide a unique deployment identity and version.

```yaml
- name: Publish Harness Memory snapshot
  env:
    HARNESS_MEMORY_API_URL: ${{ secrets.HARNESS_MEMORY_API_URL }}
    HARNESS_MEMORY_API_TOKEN: ${{ secrets.HARNESS_MEMORY_API_TOKEN }}
    HARNESS_MEMORY_ENVIRONMENT: production
    HARNESS_MEMORY_PROJECT_KEY: payments
    HARNESS_MEMORY_DEPLOYMENT_ID: ${{ github.run_id }}
    HARNESS_MEMORY_VERSION: ${{ github.sha }}
  run: |
    npm --prefix sdk ci
    npm --prefix sdk run build
    node sdk/dist/cli/index.js publish \
      --model gpt-5 \
      --effort high \
      --output json
```

The SDK also recognizes `GITHUB_RUN_ID` and `GITHUB_SHA` automatically when explicit deployment and version variables are absent.

## What the SDK sends to the LLM

The Git collector requires a Git work tree and sends the LLM:

- The resolved head commit SHA.
- The optional base and head refs.
- Added, modified, deleted, and renamed file paths from the diff.
- Sorted tracked text files with their paths, normalized contents, and SHA-256 hashes.

The collector skips `.git`, `node_modules`, `dist`, `build`, `coverage`, `venv`, and `.venv`. It also skips files matching `.pem`, `.key`, `.pkcs12`, `.pfx`, `id_rsa`, `.env*`, `.secret`, or `.credential`. Binary files are skipped.

Symlink targets must remain inside the repository. Path escapes and context budgets fail the run instead of reading outside the repository.

Default collection limits are 2,000 files and 10 MiB. Increase them only when the repository requires it:

```bash
node sdk/dist/cli/index.js publish \
  --max-files 5000 \
  --max-bytes 52428800 \
  --model gpt-5 \
  --effort high \
  --environment production \
  --project-key payments \
  --deployment-id deploy-123 \
  --version v1.2.3 \
  --dry-run
```

The child LLM process receives a sanitized environment. Variables whose names contain `TOKEN`, `SECRET`, `PASSWORD`, `KEY`, or `AUTH` are removed. The selected runner extracts one final response, which must contain a JSON graph document. Markdown fences, explanatory text, or empty output fail validation.

## Graph contract

The LLM output must contain `schema_version: "1.0"` and three arrays:

```json
{
  "schema_version": "1.0",
  "entities": [
    {"key": "payments-api", "type": "service", "name": "Payments API"}
  ],
  "relations": [],
  "evidence": []
}
```

Allowed entity types:

`project`, `system`, `service`, `api`, `event`, `library`, `team`

Allowed relation types:

`part_of`, `owned_by`, `provides`, `consumes`, `depends_on`, `publishes`, `subscribes_to`, `implements`

Allowed provenance values:

`declared`, `inferred`, `observed`, `manual`

Validation enforces unique entity keys, unique relation refs, existing relation endpoints, existing evidence relation refs, metadata JSON objects, and size limits. The validator sorts facts and object keys before calculating the deterministic `payload_sha256`.

## Publication behavior

The REST client sends:

```text
POST /v1/knowledge-publications
Authorization: Bearer <service-account-token>
Content-Type: application/json
```

The API derives tenant identity from the token owner. Tenant flags and tenant fields are not accepted by the SDK. These flags are deliberately rejected: `--tenant`, `--tenant-id`, `--token`, `--prompt`, `--interactive`, `--database`, `--db-url`, and `--postgres`.

Use HTTPS for non-localhost API URLs. HTTP is allowed only for `localhost`, `127.0.0.1`, and `::1`.

Publication results are idempotent by the API's project, environment, and deployment identity:

- `201`: `ACTIVATED`; a new snapshot became current.
- `200`: `ALREADY_PUBLISHED`; a completed retry returned the existing publication.
- `409`: `CONFLICT`; the deployment identity carries different content. The SDK does not retry it.

The client retries timeouts, HTTP 408, HTTP 429, and HTTP 5xx responses with bounded exponential backoff. It does not retry authentication, authorization, validation, or conflict errors.

## Output and exit codes

Use JSON output in automation:

```bash
node sdk/dist/cli/index.js publish <options> --output json
```

The JSON result includes status, publication and snapshot identifiers when available, project, environment, deployment, version, payload SHA-256, and entity/relation/evidence counts.

| Code | Meaning | Typical action |
| ---: | --- | --- |
| `0` | Success or already published | Continue. |
| `2` | Usage or configuration error | Fix flags, required values, or configuration. |
| `3` | Git context collection error | Check repository, refs, symlinks, and limits. |
| `4` | LLM execution error | Check command, model, timeout, and pure JSON stdout. |
| `5` | Graph validation error | Fix schema, keys, refs, types, or metadata. |
| `6` | API authentication or scope error | Use an active tenant-bound token with `memory:publish`. |
| `7` | Deployment conflict | Use a new deployment ID or publish the original content. |
| `8` | API failure or exhausted retries | Check API health, URL, network, and server logs. |
| `130` | Interrupted by SIGINT or SIGTERM | Retry only when the deployment is safe to retry. |

## Programmatic use

The package exports the use case, ports, domain contracts, and default adapters:

```typescript
import {
  GraphValidator,
  GitContextCollector,
  LocalLlmRunner,
  PublishSnapshotUseCase,
  RestPublicationClient,
} from "@harness-memory/sdk";

const apiUrl = process.env.HARNESS_MEMORY_API_URL;
const token = process.env.HARNESS_MEMORY_API_TOKEN;

if (!apiUrl || !token) {
  throw new Error("HARNESS_MEMORY_API_URL and HARNESS_MEMORY_API_TOKEN are required");
}

const publisher = new PublishSnapshotUseCase(
  new GitContextCollector(),
  new LocalLlmRunner(),
  new GraphValidator(),
  new RestPublicationClient(),
);

const result = await publisher.execute({
  repository: ".",
  projectKey: "payments",
  environment: "production",
  deploymentId: "deploy-123",
  version: "v1.2.3",
  agent: "codex-cli",
  model: "gpt-5",
  effort: "high",
  headRef: "HEAD",
  dryRun: false,
  apiUrl,
  token,
});

console.log(result);
```

Use `dryRun: true` to omit `apiUrl` and `token` and stop before the REST adapter.

## Useful commands

Run from `sdk/`:

```bash
npm ci                  # Install the locked dependency set
npm run build           # Compile TypeScript into dist/
npm test                # Run all Vitest tests
npm run test:unit       # Unit tests
npm run test:integration # Integration tests
npm run test:e2e        # End-to-end CLI tests
```

Run focused checks from the repository root:

```bash
npm --prefix sdk run build
npm --prefix sdk test
```

## Troubleshooting

- Missing required values or an unknown/forbidden flag returns code `2`.
- `--effort` must be exactly `low`, `medium`, `high`, or `xhigh`.
- A real publication needs both `--api-url` and the token environment variable.
- A real non-local API URL must use `https://`.
- A token without the exact `memory:publish` scope returns code `6`.
- A custom LLM command must accept the streamed JSON input and emit only one JSON graph document on stdout.
- Run `--dry-run --output text --verbose` before publishing to inspect local collection and synthesis behavior.

## Related documentation

- [API README](../api/README.md): credential management and publication endpoint.
- [Snapshot Publisher feature](../docs/feature/sdk/snapshot-publisher.md): implementation contract and architecture map.
- [Security architecture](../docs/adr/SECURITY.md): token, scope, tenant, and secret rules.
- [Project README](../README.md): complete Harness Memory setup and MCP usage.
