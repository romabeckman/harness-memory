---
doc_type: adr
domain: testing
stack: [Python 3.12+, FastMCP 4.x, PostgreSQL, Alembic]
node_id: "adr:tests"
tags: [testing, unit-tests, e2e-tests, coverage]
edges: []
updated: 2026-09-18
---
# Testing Protocol

## OVERVIEW

Use separate **unit**, **integration**, **end-to-end**, and **MCP contract** tests.
Cover domain entities/value objects, application handlers/contracts, PostgreSQL models/repositories, migrations, tenant isolation, and MCP schemas.
REQUIRED: Enforce **80% minimum coverage** for each listed layer and globally.

## COMMANDS

No `pyproject.toml`, test runner, coverage tool, CI file, or test command exists.
Add commands only when project tooling exists.

| Type | Command | Description |
|------|---------|-------------|
| Unit | Not configured | Test entities, value objects, domain services, application handlers, and Pydantic inbound/outbound contracts. |
| Integration | Not configured | Test PostgreSQL models/repositories, snapshot activation, transactions, tenant isolation, and migrations. |
| E2E / MCP | Not configured | Test public MCP tools, resources, prompts, and adapter-to-application mapping through FastMCP. |
| Coverage | Not configured | Add a coverage command that enforces 80% domain, application, infrastructure, and global coverage. |

Verified migration commands from project scope: `harness-memory migrate` and `harness-memory migrate --status`.

## MINIMUM COVERAGE

REQUIRED: Maintain the following minimum coverage levels:

| Layer | Coverage | Description |
|-------|----------|-------------|
| Domain / Core | 80% | Entities, value objects, domain services, invariants, and impact rules. |
| Application / Use Cases | 80% | Handlers, inbound/outbound contracts, ports, and orchestration. |
| Infrastructure / Adapters | 80% | PostgreSQL models, repositories, transactions, migrations, and MCP adapters. |
| Global | 80% | Total measured project coverage. |

No CI gate exists in the repository yet. Add a CI gate before treating 80% as release-enforced.

## PATTERNS & BEST PRACTICES

REQUIRED: Use Arrange, Act, Assert with one behavior per test.
REQUIRED: Test domain entities/value objects without infrastructure and application handlers through fake/mock ports.
REQUIRED: Test snapshot immutability, versioning, idempotent publication, invalid input rejection, and active replacement.
REQUIRED: Use real PostgreSQL behavior for models, repositories, transactions, migrations, and tenant isolation.
REQUIRED: Use the FastMCP in-process client for MCP catalog and schema tests.
REQUIRED: Assert provenance and evidence in relationship and impact results.
PROHIBITED: Mock domain logic or hide transaction behavior behind broad mocks.
PROHIBITED: Depend on test execution order or shared tenant data.

## TOOLING

- **Framework:** Python 3.12+ and FastMCP 4.x; test framework not configured.
- **Assertions:** Not configured; select with the project test runner.
- **Mocks/Stubs:** Not specified; mock external boundaries only after tooling is added.
- **Coverage:** Coverage tool and report format not configured; enforce 80% minimum.
- **CI Integration:** No CI configuration exists in the repository.

## TROUBLESHOOTING

- **Flaky tests:** Isolate the failing tier, record database state and tenant identity, then report the failure after the runner exists.
- **Debug mode:** No debug command is configured. Add the runner's verbose mode with the test tooling.

## REFERENCES

- [**README.md**](../README.md): Documentation navigation index.
- [**ARCHITECTURE.md**](./ARCHITECTURE.md): System boundaries and dependency rules.
