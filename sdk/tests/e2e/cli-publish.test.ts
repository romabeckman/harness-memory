import { createServer, Server } from "node:http";
import { join, resolve } from "node:path";
import { mkdtempSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { execFileSync } from "node:child_process";
import { describe, expect, it, afterEach, beforeEach, vi } from "vitest";
import { CliApp } from "../../src/cli/cli-app.js";
import { ExitCode } from "../../src/domain/exit-code.js";

describe("CLI Publish E2E Scenarios (AC 1 - 9)", () => {
  let server: Server;
  let serverUrl: string;
  let apiCalls: number;
  let baselineCalls: number;
  let temporary: string;
  let repository: string;
  let lastRequestBody: any;

  beforeEach(async () => {
    apiCalls = 0;
    baselineCalls = 0;
    temporary = mkdtempSync(join(tmpdir(), "memory-cli-e2e-"));
    repository = join(temporary, "repository");
    execFileSync("git", ["clone", "--local", "--quiet", resolve("../"), repository]);
    server = createServer((req, res) => {
      if (req.method === "GET" && req.url?.startsWith("/v1/knowledge-publications/latest?")) {
        baselineCalls++;
        res.writeHead(404);
        res.end();
        return;
      }
      if (req.method === "POST") apiCalls++;
      let data = "";
      req.on("data", (chunk) => {
        data += chunk;
      });
      req.on("end", () => {
        lastRequestBody = data ? JSON.parse(data) : null;
        if (req.url === "/v1/knowledge-publications") {
          if (lastRequestBody?.deployment_id === "conflict-dep") {
            res.writeHead(409, { "Content-Type": "application/json" });
            res.end(JSON.stringify({ detail: "deployment conflict" }));
            return;
          }
          if (lastRequestBody?.deployment_id === "already-dep") {
            res.writeHead(200, { "Content-Type": "application/json" });
            res.end(
              JSON.stringify({
                status: "ALREADY_PUBLISHED",
                project_key: lastRequestBody.project_key,
                environment: lastRequestBody.environment,
                deployment_id: lastRequestBody.deployment_id,
                version: lastRequestBody.version,
              })
            );
            return;
          }
          res.writeHead(201, { "Content-Type": "application/json" });
          res.end(
            JSON.stringify({
              status: "ACTIVATED",
              publication_id: "pub-123",
              snapshot_id: "snap-123",
              project_key: lastRequestBody.project_key,
              environment: lastRequestBody.environment,
              deployment_id: lastRequestBody.deployment_id,
              version: lastRequestBody.version,
            })
          );
        } else {
          res.writeHead(404);
          res.end();
        }
      });
    });

    await new Promise<void>((resolve) => {
      server.listen(0, "127.0.0.1", () => {
        const addr = server.address() as any;
        serverUrl = `http://127.0.0.1:${addr.port}`;
        resolve();
      });
    });
  });

  afterEach(async () => {
    await new Promise<void>((resolve) => server.close(() => resolve()));
    rmSync(temporary, { recursive: true, force: true });
  });

  it("AC 1: publishes valid graph through API and exits 0", async () => {
    const stdoutLines: string[] = [];
    const stderrLines: string[] = [];
    const app = new CliApp({
      stdout: (msg) => stdoutLines.push(msg),
      stderr: (msg) => stderrLines.push(msg),
      env: {
        HARNESS_MEMORY_API_KEY: "valid-publish-token",
      },
    });

    const fakeLlmCommand = `node ${resolve("tests/fixtures/fake-llm.cjs")}`;

    const code = await app.run([
      "publish",
      "--agent", "codex-cli",
      "--model",
      "gpt-5",
      "--effort",
      "high",
      "--environment",
      "staging",
      "--project-key",
      "payments",
      "--deployment-id",
      "deploy-ac1",
      "--version",
      "v1.0.0",
      "--api-url",
      serverUrl,
      "--repository",
      repository,
      "--llm-command",
      fakeLlmCommand,
      "--output",
      "json",
    ]);

    expect(code).toBe(ExitCode.SUCCESS);
    expect(apiCalls).toBe(1);
    expect(baselineCalls).toBe(1);
    expect(lastRequestBody).not.toHaveProperty("project_memory");
    expect(lastRequestBody.entities.some((entity: any) => entity.type === "feature" && entity.metadata.content)).toBe(true);
    const parsedStdout = JSON.parse(stdoutLines.join("\n"));
    expect(parsedStdout.status).toBe("ACTIVATED");
    expect(parsedStdout.project_key).toBe("payments");
  });

  it("AC 5: returns ALREADY_PUBLISHED and exits 0 on duplicate deployment", async () => {
    const stdoutLines: string[] = [];
    const app = new CliApp({
      stdout: (msg) => stdoutLines.push(msg),
      stderr: () => {},
      env: { HARNESS_MEMORY_API_KEY: "valid-token" },
    });

    const fakeLlmCommand = `node ${resolve("tests/fixtures/fake-llm.cjs")}`;

    const code = await app.run([
      "--agent", "codex-cli",
      "--model",
      "gpt-5",
      "--effort",
      "high",
      "--environment",
      "staging",
      "--project-key",
      "payments",
      "--deployment-id",
      "already-dep",
      "--version",
      "v1.0.0",
      "--api-url",
      serverUrl,
      "--repository",
      repository,
      "--llm-command",
      fakeLlmCommand,
      "--output",
      "json",
    ]);

    expect(code).toBe(ExitCode.SUCCESS);
    const parsedStdout = JSON.parse(stdoutLines.join("\n"));
    expect(parsedStdout.status).toBe("ALREADY_PUBLISHED");
  });

  it("AC 6: exits 7 on deployment conflict (409)", async () => {
    const stderrLines: string[] = [];
    const app = new CliApp({
      stdout: () => {},
      stderr: (msg) => stderrLines.push(msg),
      env: { HARNESS_MEMORY_API_KEY: "valid-token" },
    });

    const fakeLlmCommand = `node ${resolve("tests/fixtures/fake-llm.cjs")}`;

    const code = await app.run([
      "--agent", "codex-cli",
      "--model",
      "gpt-5",
      "--effort",
      "high",
      "--environment",
      "staging",
      "--project-key",
      "payments",
      "--deployment-id",
      "conflict-dep",
      "--version",
      "v1.0.0",
      "--api-url",
      serverUrl,
      "--repository",
      repository,
      "--llm-command",
      fakeLlmCommand,
    ]);

    expect(code).toBe(ExitCode.CONFLICT);
    expect(stderrLines.some((l) => l.includes("Deployment conflict"))).toBe(true);
  });

  it("AC 7: never publishes invalid model output after reading baseline", async () => {
    const stderrLines: string[] = [];
    const app = new CliApp({
      stdout: () => {},
      stderr: (msg) => stderrLines.push(msg),
      env: { HARNESS_MEMORY_API_KEY: "valid-token" },
    });

    // In this test, we test that invalid graph output causes validator to reject
    // and no publication POST is made
    const code = await app.run([
      "--agent", "codex-cli",
      "--model",
      "gpt-5",
      "--effort",
      "high",
      "--environment",
      "staging",
      "--project-key",
      "payments",
      "--deployment-id",
      "dep-val-fail",
      "--version",
      "v1.0.0",
      "--api-url",
      serverUrl,
      "--repository",
      repository,
      "--llm-command",
      process.execPath,
    ]);

    // When node runs without script args, it exits with invalid JSON / error -> exits 4 or 5
    // Baseline read is permitted, publication is not.
    expect(apiCalls).toBe(0);
    expect(baselineCalls).toBe(1);
    expect([ExitCode.LLM_EXECUTION, ExitCode.VALIDATION]).toContain(code);
  });

  it("AC 9: exits 2 on unknown or forbidden flags", async () => {
    const stderrLines: string[] = [];
    const app = new CliApp({
      stdout: () => {},
      stderr: (msg) => stderrLines.push(msg),
    });

    const codeTenant = await app.run(["--tenant", "tenant-1"]);
    expect(codeTenant).toBe(ExitCode.USAGE_OR_CONFIG);

    const codeUnknown = await app.run(["--invalid-custom-flag"]);
    expect(codeUnknown).toBe(ExitCode.USAGE_OR_CONFIG);
  });
});
