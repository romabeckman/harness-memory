import { describe, expect, it } from "vitest";
import { ExitCode } from "../../../src/domain/exit-code.js";

describe("ExitCode", () => {
  it("defines standard process exit codes per Section 16", () => {
    expect(ExitCode.SUCCESS).toBe(0);
    expect(ExitCode.USAGE_OR_CONFIG).toBe(2);
    expect(ExitCode.CONTEXT_COLLECTION).toBe(3);
    expect(ExitCode.LLM_EXECUTION).toBe(4);
    expect(ExitCode.VALIDATION).toBe(5);
    expect(ExitCode.API_AUTH).toBe(6);
    expect(ExitCode.CONFLICT).toBe(7);
    expect(ExitCode.API_SERVER_OR_RETRY_EXHAUSTED).toBe(8);
    expect(ExitCode.INTERRUPTED).toBe(130);
  });
});
