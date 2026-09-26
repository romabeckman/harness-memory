import { LlmExecutionError } from "../../domain/llm-execution-error.js";
import { LlmAgentRunner, LlmAgentRunnerOptions } from "./llm-agent-runner.js";

export class AntigravityCliRunner implements LlmAgentRunner {
  public readonly type = "antigravity-cli" as const;
  public readonly command = "agy";

  public buildArgs(options: LlmAgentRunnerOptions): string[] {
    const timeoutMs = ((options.timeoutSeconds ?? 600) + 1) * 1000;
    return [
      "--model",
      options.model,
      "--effort",
      options.effort,
      "--output-format",
      "json",
      "--print-timeout",
      `${timeoutMs}ms`,
      "--dangerously-skip-permissions",
    ];
  }

  public parseOutput(stdout: string): string {
    const trimmed = stdout.trim();
    if (!trimmed) {
      throw new LlmExecutionError("Antigravity CLI emitted empty stdout");
    }

    let parsed: unknown;
    try {
      parsed = JSON.parse(trimmed);
    } catch {
      return trimmed;
    }

    if (parsed === null || typeof parsed !== "object") return trimmed;

    const response = parsed as Record<string, unknown>;
    const responseText = typeof response.response === "string" ? response.response.trim() : "";
    if (response.status === "FAILED" || (response.status === "ERROR" && !responseText)) {
      throw new LlmExecutionError("Antigravity CLI returned an error");
    }
    if (responseText) return responseText;
    if (
      "schema_version" in response &&
      "entities" in response &&
      "relations" in response &&
      "evidence" in response
    ) {
      return trimmed;
    }
    throw new LlmExecutionError("Antigravity CLI response omitted final result text");
  }
}
