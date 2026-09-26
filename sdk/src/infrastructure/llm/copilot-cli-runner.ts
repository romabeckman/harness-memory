import { LlmExecutionError } from "../../domain/llm-execution-error.js";
import { LlmAgentRunner, LlmAgentRunnerOptions } from "./llm-agent-runner.js";

export class CopilotCliRunner implements LlmAgentRunner {
  public readonly type = "copilot-cli" as const;
  public readonly command = "copilot";
  public readonly promptTransport = "argument" as const;

  public buildArgs(options: LlmAgentRunnerOptions, prompt?: string): string[] {
    if (prompt === undefined) {
      throw new LlmExecutionError("Copilot CLI prompt text is required");
    }

    return [
      "--allow-all",
      "--autopilot",
      "--output-format",
      "json",
      "--model",
      options.model,
      "--reasoning-effort",
      options.effort,
      "--prompt",
      prompt,
    ];
  }

  public parseOutput(stdout: string): string {
    const trimmed = stdout.trim();
    if (!trimmed) {
      throw new LlmExecutionError("Copilot CLI emitted empty stdout");
    }

    try {
      const parsed: unknown = JSON.parse(trimmed);
      if (
        parsed !== null &&
        typeof parsed === "object" &&
        "schema_version" in parsed &&
        "entities" in parsed &&
        "relations" in parsed &&
        "evidence" in parsed
      ) {
        return trimmed;
      }
    } catch {
      // Copilot emits JSONL events; parse assistant messages below.
    }

    let finalMessage = "";
    let isSuccess = true;
    for (const line of trimmed.split(/\r?\n/)) {
      try {
        const event: unknown = JSON.parse(line);
        if (!event || typeof event !== "object") continue;

        const eventRecord = event as Record<string, unknown>;
        if (eventRecord.type === "assistant.message") {
          const data = eventRecord.data as Record<string, unknown> | undefined;
          if (typeof data?.content === "string") finalMessage = data.content;
        } else if (
          eventRecord.type === "result"
        ) {
          isSuccess = eventRecord.exitCode === 0;
        }
      } catch {
        // Ignore progress lines that are not JSON events.
      }
    }

    if (!isSuccess) throw new LlmExecutionError("Copilot CLI returned an error");
    if (!finalMessage.trim()) {
      throw new LlmExecutionError("Copilot CLI did not emit a final assistant message");
    }
    return finalMessage.trim();
  }
}
