---
doc_type: adr
domain: testing
stack: [Python 3.12+, pytest 9.x, pytest-asyncio, pytest-cov, coverage.py, FastMCP 4.x, PostgreSQL]
node_id: "adr:tests"
tags: [testing, unit-tests, e2e-tests, coverage]
edges: []
updated: 2026-09-19
---
# Testing Protocol

## OVERVIEW

Use **pytest 9.x** across unit, PostgreSQL integration, MCP contract, and HTTP/Docker E2E tiers. Enforce branch coverage globally for `core` and `mcp`.

## COMMANDS

| Type | Command | Description |
|------|---------|-------------|
| Unit | `./venv/bin/python -m pytest tests/unit` | Domain, application, adapter, security, and configuration tests. |
| Integration | `./venv/bin/python -m pytest tests/integration` | PostgreSQL repositories, migrations, startup checks, and telemetry integration. |
| E2E | `./venv/bin/python -m pytest tests/e2e` | FastMCP catalog/contracts, HTTP security, and Docker checks. |
| Coverage | `./venv/bin/python -m pytest --cov=core --cov=mcp --cov-branch --cov-fail-under=80` | Branch coverage with global 80% gate. |
| Migration | `harness-memory migrate` / `harness-memory migrate --status` | Upgrade or inspect Alembic schema state. |

## MINIMUM COVERAGE

REQUIRED: Maintain the configured global threshold. No independent per-layer gates exist.

| Layer | Coverage | Description |
|-------|----------|-------------|
| Domain / Core | Report only | Included in global `core` measurement. |
| Application / Use Cases | Report only | Included in global `core` measurement. |
| Infrastructure / Adapters | Report only | Included in `core` and `mcp` measurement. |
| Global | 80% | Enforced by `coverage.fail_under` and CI. |

## PATTERNS & BEST PRACTICES

REQUIRED: Keep unit tests independent from infrastructure; test handlers through ports and domain rules directly.
REQUIRED: Use real PostgreSQL for repository, migration, transaction, tenant-isolation, and schema-plan behavior.
REQUIRED: Use FastMCP in-process clients for catalog and contract tests; use HTTP E2E for production authentication flows.
REQUIRED: Assert bounded output, provenance, evidence, authorization, tenant isolation, and sanitized failures.
PROHIBITED: Mock domain behavior or rely on test execution order.
PROHIBITED: Treat skipped PostgreSQL checks as proof of production persistence behavior.

## TOOLING

- **Framework:** Python 3.12+, pytest 9.x, pytest-asyncio, FastMCP 4.x.
- **Assertions:** pytest built-in assertions.
- **Mocks/Stubs:** Hand-written fakes and boundary substitutes; no mocking library configured.
- **Coverage:** coverage.py with pytest-cov; branch measurement and missing-line report.
- **CI Integration:** GitHub Actions runs Ruff, PostgreSQL migrations, unit, integration, E2E, and coverage jobs.

## TROUBLESHOOTING

- **Flaky tests:** Isolate the tier, verify `TEST_DATABASE_URL`, tenant data, migration revision, and request context; rerun the focused test.
- **Debug mode:** `./venv/bin/python -m pytest -vv -s <test-path>`.

<!-- DOCUMENT MAP: omitted because this baseline ADR has no graph edge. -->

## REFERENCES

- [**README.md**](../README.md): Main documentation index.
- [**ARCHITECTURE.md**](./ARCHITECTURE.md): System architecture and dependency rules.
