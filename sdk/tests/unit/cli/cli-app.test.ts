import { describe, expect, it, vi } from "vitest";
import { CliApp } from "../../../src/cli/cli-app.js";
import { ExitCode } from "../../../src/domain/exit-code.js";

describe("CliApp", () => {
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
});
