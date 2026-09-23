import { afterEach, describe, expect, it, vi } from "vitest";
import { CliApp } from "../../../src/cli/cli-app.js";
import { PublishSnapshotUseCase } from "../../../src/application/publish-snapshot/publish-snapshot.use-case.js";
import { ExitCode } from "../../../src/domain/exit-code.js";
import { GraphValidationError } from "../../../src/domain/graph-validation-error.js";

describe("CliApp", () => {
  afterEach(() => vi.restoreAllMocks());

  it("returns exit code 2 when required CLI arguments are missing", async () => {
    const stdoutMock = vi.fn();
    const stderrMock = vi.fn();
    const app = new CliApp({ stdout: stdoutMock, stderr: stderrMock });

    const code = await app.run([]);
    expect(code).toBe(ExitCode.USAGE_OR_CONFIG);
    expect(stderrMock).toHaveBeenCalled();
  });

  it("returns exit code 2 when forbidden --tenant flag is supplied", async () => {
    const stdoutMock = vi.fn();
    const stderrMock = vi.fn();
    const app = new CliApp({ stdout: stdoutMock, stderr: stderrMock });

    const code = await app.run(["--tenant", "tenant-1"]);
    expect(code).toBe(ExitCode.USAGE_OR_CONFIG);
    expect(stderrMock).toHaveBeenCalledWith(expect.stringContaining("Forbidden flag"));
  });

  it("returns exit code 2 when unknown flag is supplied", async () => {
    const stdoutMock = vi.fn();
    const stderrMock = vi.fn();
    const app = new CliApp({ stdout: stdoutMock, stderr: stderrMock });

    const code = await app.run(["--invalid-xyz"]);
    expect(code).toBe(ExitCode.USAGE_OR_CONFIG);
    expect(stderrMock).toHaveBeenCalledWith(expect.stringContaining("Unknown flag"));
  });

  it("prints phase diagnostics to stderr while keeping JSON output clean with --debug", async () => {
    vi.spyOn(PublishSnapshotUseCase.prototype, "execute").mockImplementation(async (_options, progress) => {
      progress?.({ phase: "Collecting repository context", state: "started" });
      progress?.({ phase: "Collecting repository context", state: "completed" });
      return { status: "DRY_RUN", projectKey: "send", environment: "production",
        deploymentId: "test-123", version: "v0.0.1", payloadSha256: "hash" };
    });
    const stdout: string[] = [];
    const stderr: string[] = [];
    const app = new CliApp({ stdout: line => stdout.push(line), stderr: line => stderr.push(line) });

    const code = await app.run(["publish", "--agent", "codex-cli", "--debug", "--output", "json"]);

    expect(code).toBe(ExitCode.SUCCESS);
    expect(JSON.parse(stdout.join("\n")).status).toBe("DRY_RUN");
    expect(stderr.join("\n")).toContain("[debug] Phase Collecting repository context completed in");
    expect(stdout.join("\n")).not.toContain("[debug]");
  });

  it("prints a redacted error stack only when --debug is enabled", async () => {
    vi.spyOn(PublishSnapshotUseCase.prototype, "execute")
      .mockRejectedValue(new GraphValidationError("entity key is required; token=private-value; api=https://alice:pw@localhost"));
    const debugLines: string[] = [];
    const normalLines: string[] = [];
    const env = { HARNESS_MEMORY_API_KEY: "private-value" };
    const debugApp = new CliApp({ stderr: line => debugLines.push(line), stdout: vi.fn(), env });
    const normalApp = new CliApp({ stderr: line => normalLines.push(line), stdout: vi.fn(), env });

    expect(await debugApp.run(["--agent", "codex-cli", "--debug"])).toBe(ExitCode.VALIDATION);
    expect(await normalApp.run(["--agent", "codex-cli"])).toBe(ExitCode.VALIDATION);
    expect(debugLines.join("\n")).toContain("[debug] Error stack:");
    expect(debugLines.join("\n")).toMatch(/\bat\s+.*cli-app\.test/);
    expect(debugLines.join("\n")).not.toContain("private-value");
    expect(debugLines.join("\n")).not.toContain("alice:pw");
    expect(normalLines.join("\n")).not.toContain("[debug]");
    expect(normalLines.join("\n")).not.toContain("private-value");
    expect(normalLines.join("\n")).not.toContain("alice:pw");
  });
});
