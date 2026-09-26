import { LlmExecutionError } from "../../domain/llm-execution-error.js";
import { LlmAgentRunner, LlmAgentRunnerOptions } from "./llm-agent-runner.js";

export class ClaudeCliRunner implements LlmAgentRunner {
  public readonly type = "claude-cli" as const;
  public readonly command = "claude";

  public buildArgs(options: LlmAgentRunnerOptions): string[] {
    return [
      "--print",
      "--output-format",
      "json",
      "--input-format",
      "text",
      "--model",
      options.model,
      "--effort",
      options.effort,
    ];
  }

  public parseOutput(stdout: string): string {
    const trimmed = stdout.trim();
    if (!trimmed) {
      throw new LlmExecutionError("Claude CLI emitted empty stdout");
    }

    try {
      const parsed: unknown = JSON.parse(trimmed);
      if (parsed !== null && typeof parsed === "object") {
        const response = parsed as Record<string, unknown>;
        if (response.is_error === true || response.subtype === "error") {
          throw new LlmExecutionError("Claude CLI returned an error");
        }

        const result = response.result;
        if (typeof result === "string") return result.trim();
        if (
          "schema_version" in response &&
          "entities" in response &&
          "relations" in response &&
          "evidence" in response
        ) {
          return trimmed;
        }
        throw new LlmExecutionError("Claude CLI response omitted final result text");
      }
    } catch (error) {
      if (error instanceof LlmExecutionError) throw error;
      // Pass plain text to graph JSON parsing for a focused validation error.
    }

    return trimmed;
  }
}
