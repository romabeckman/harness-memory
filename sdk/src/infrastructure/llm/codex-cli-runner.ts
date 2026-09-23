import { LlmInvocationOptions } from "../../application/ports/llm-runner.port.js";
import { LlmExecutionError } from "../../domain/llm-execution-error.js";
import { LlmAgentRunner } from "./llm-agent-runner.js";

export class CodexCliRunner implements LlmAgentRunner {
  public readonly type = "codex-cli" as const;
  public readonly command =
    process.platform === "win32" ? "cmd.exe /d /s /c codex" : "codex";

  public buildArgs(options: Pick<LlmInvocationOptions, "model" | "effort">): string[] {
    return [
      "exec",
      "--json",
      "--model",
      options.model,
      "--config",
      `model_reasoning_effort=\"${options.effort}\"`,
      "-",
    ];
  }

  public parseOutput(stdout: string): string {
    const trimmed = stdout.trim();
    if (!trimmed) {
      throw new LlmExecutionError("Codex CLI emitted empty stdout");
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
      // Codex emits JSONL events; parse them below.
    }

    let finalResult = "";
    for (const line of trimmed.split(/\r?\n/)) {
      try {
        const event: unknown = JSON.parse(line);
        if (!event || typeof event !== "object") continue;

        const eventRecord = event as Record<string, unknown>;
        const item = eventRecord.item as Record<string, unknown> | undefined;
        if (
          (eventRecord.type === "item.completed" || eventRecord.type === "item.started") &&
          item?.type === "agent_message" &&
          typeof item.text === "string"
        ) {
          finalResult = item.text;
        }
        if (
          (eventRecord.type === "result" || eventRecord.type === "turn.completed") &&
          typeof eventRecord.result === "string"
        ) {
          finalResult = eventRecord.result;
        }
      } catch {
        // Ignore non-JSON progress lines.
      }
    }

    if (!finalResult.trim()) {
      throw new LlmExecutionError("Codex CLI did not emit a final text response");
    }
    return finalResult.trim();
  }
}
