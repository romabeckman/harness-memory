---
doc_type: adr
domain: testing
stack: [Python 3.12+, pytest 9.x, pytest-asyncio, pytest-cov, coverage.py, TypeScript 7.x SDK, TypeScript 5.x Web, Node.js 20+, Vitest 4.x SDK, Vitest 1.6.x Web, Playwright, FastAPI, FastMCP 4.x, PostgreSQL]
node_id: "adr:tests"
tags: [testing, unit-tests, e2e-tests, coverage]
edges: []
updated: 2026-09-26
---
# Testing Protocol

## OVERVIEW

Use **pytest 9.x** for Python unit, PostgreSQL integration, FastAPI/FastMCP contract, and HTTP/Docker E2E tiers. Use **Vitest 4.x** for SDK tests and **Vitest 1.6.x** for Web tests. Use **Playwright** for Web E2E. Enforce the configured Python branch-coverage gate.

## COMMANDS

| Type | Command | Description |
|------|---------|-------------|
| Python unit | `./venv/bin/python -m pytest tests/unit` | Domain, application, adapter, security, and configuration tests. |
| Python integration | `./venv/bin/python -m pytest tests/integration` | PostgreSQL repositories, migrations, startup checks, and telemetry integration. |
| Python E2E | `./venv/bin/python -m pytest tests/e2e` | FastMCP catalog/contracts, HTTP security, and Docker checks. |
| SDK dependencies | `npm install` from `sdk/` | Verify and install locked SDK dependencies before SDK checks. |
| SDK lint | `npm run lint` from `sdk/` | ESLint syntax and style checks. |
| SDK build | `npm run build` from `sdk/` | Compile SDK declarations and output. |
| SDK typecheck | `npm run typecheck` from `sdk/` | Type check without emitting output. |
| SDK unit | `npm --prefix sdk run test:unit` | SDK application, CLI, and adapter unit tests. |
| SDK integration | `npm --prefix sdk run test:integration` | SDK process, storage, and HTTP boundary tests. |
| SDK E2E | `npm --prefix sdk run test:e2e` | SDK CLI publication flow. |
| SDK all tiers | `npm --prefix sdk run test` | Run all SDK Vitest tests. |
| Web unit | `npm --prefix web run test` | Web domain, application, and infrastructure Vitest unit tests. |
| Web E2E | `npm --prefix web run test:e2e` | Web Playwright end-to-end admin console tests. |
| Coverage | `./venv/bin/python -m pytest --cov=api --cov=core --cov=harness_memory_mcp --cov-branch --cov-fail-under=80` | Backend branch coverage with global 80% gate. |
| Migration | `harness-memory migrate` / `harness-memory migrate --status` | Upgrade or inspect Alembic schema state. |

For SDK changes, run dependency install, lint, build, typecheck, then tests in that order.

## MINIMUM COVERAGE

REQUIRED: Maintain the configured backend threshold. No independent per-layer, SDK, or Web coverage gates exist.

| Layer | Coverage | Description |
|-------|----------|-------------|
| Domain / Core | Report only | Included in global `core` measurement. |
| Application / Use Cases | Report only | Included in global `core` measurement. |
| Infrastructure / Adapters | Report only | Included in `core` and `harness_memory_mcp` measurement. |
| Global | 80% | Enforced across `api`, `core`, and `harness_memory_mcp`. |

## PATTERNS & BEST PRACTICES

REQUIRED: Keep unit tests independent from infrastructure; test handlers through ports and domain rules directly.
REQUIRED: Use real PostgreSQL for repository, migration, transaction, tenant-isolation, and schema-plan behavior.
REQUIRED: Use FastMCP in-process clients for catalog and contract tests; use HTTP E2E for production authentication flows.
REQUIRED: Assert bounded output, provenance, evidence, authorization, tenant isolation, and sanitized failures.
REQUIRED: Isolate Web E2E tests using mock or test environments (`.env.test`).
PROHIBITED: Mock domain behavior or rely on test execution order.
PROHIBITED: Treat skipped PostgreSQL checks as proof of production persistence behavior.

## TOOLING

- **Framework:** pytest 9.x, pytest-asyncio, FastMCP 4.x; Vitest 4.x for the SDK, Vitest 1.6.x for Web, and Playwright for Web E2E.
- **Assertions:** pytest and Vitest built-in assertions; Playwright `expect`.
- **Mocks/Stubs:** Hand-written fakes and boundary substitutes; no external mocking library configured for Python.
- **Coverage:** coverage.py with pytest-cov; branch measurement and missing-line report.
- **CI Integration:** GitHub Actions runs Ruff, PostgreSQL migrations, Python unit, integration, E2E, and coverage jobs. Run SDK and Web tiers through their package scripts.
- **Architecture:** Unit tests validate repository source rules against the real project root as well as isolated fixtures.

## TROUBLESHOOTING

- **Flaky tests:** Isolate the tier, verify `TEST_DATABASE_URL`, tenant data, migration revision, and request context; rerun the focused test.
- **Debug mode:** `./venv/bin/python -m pytest -vv -s <test-path>`.

<!-- DOCUMENT MAP: omitted because this baseline ADR has no graph edge. -->

## REFERENCES

- [**README.md**](../README.md): Main documentation index.
- [**ARCHITECTURE.md**](./ARCHITECTURE.md): System architecture and dependency rules.
