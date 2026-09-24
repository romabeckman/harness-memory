import { LlmInvocationOptions } from "../../application/ports/llm-runner.port.js";
import { LlmExecutionError } from "../../domain/llm-execution-error.js";
import { LlmAgentRunner } from "./llm-agent-runner.js";

export class AgyCliRunner implements LlmAgentRunner {
  public readonly type = "agy-cli" as const;
  public readonly command =
    process.platform === "win32" ? "cmd.exe /d /s /c agy" : "agy";

  public buildArgs(options: Pick<LlmInvocationOptions, "model" | "effort">): string[] {
    const args = ["--output-format", "json"];
    if (options.model) {
      args.push("--model", options.model);
    }
    if (options.effort) {
      args.push("--effort", options.effort);
    }
    args.push("--print", "-");
    return args;
  }

  public parseOutput(stdout: string): string {
    const trimmed = stdout.trim();
    if (!trimmed) {
      throw new LlmExecutionError("AGY CLI emitted empty stdout");
    }

    try {
      const parsed: unknown = JSON.parse(trimmed);
      if (parsed !== null && typeof parsed === "object") {
        const responseObj = parsed as Record<string, unknown>;
        if (
          responseObj.status === "ERROR" ||
          responseObj.is_error === true ||
          (typeof responseObj.error === "string" && responseObj.error.length > 0)
        ) {
          const detail = typeof responseObj.error === "string" && responseObj.error.length > 0
            ? responseObj.error
            : "Unknown error";
          throw new LlmExecutionError(`AGY CLI returned an error: ${detail}`);
        }

        const res = responseObj.response;
        if (typeof res === "string" && res.trim().length > 0) {
          return res.trim();
        }

        if (
          "schema_version" in responseObj &&
          "entities" in responseObj &&
          "relations" in responseObj &&
          "evidence" in responseObj
        ) {
          return trimmed;
        }

        throw new LlmExecutionError("AGY CLI response omitted final response text");
      }
    } catch (error) {
      if (error instanceof LlmExecutionError) throw error;
      // Fall through to plain text parsing
    }

    return trimmed;
  }
}
