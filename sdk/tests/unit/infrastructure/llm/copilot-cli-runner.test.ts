import { describe, expect, it } from "vitest";
import { LlmExecutionError } from "../../../../src/domain/llm-execution-error.js";
import { CopilotCliRunner } from "../../../../src/infrastructure/llm/copilot-cli-runner.js";

describe("CopilotCliRunner", () => {
  const runner = new CopilotCliRunner();

  it("builds non-interactive Copilot CLI arguments using model and reasoning effort", () => {
    expect(runner.buildArgs({ model: "gpt-5", effort: "high" }, "prompt payload")).toEqual([
      "--allow-all",
      "--autopilot",
      "--output-format",
      "json",
      "--model",
      "gpt-5",
      "--reasoning-effort",
      "high",
      "--prompt",
      "prompt payload",
    ]);
  });

  it("requires prompt text because Copilot receives it as an argument", () => {
    expect(() => runner.buildArgs({ model: "gpt-5", effort: "medium" })).toThrow(LlmExecutionError);
  });

  it("extracts the final assistant message from Copilot JSONL output", () => {
    const graph = JSON.stringify({ schema_version: "1.0", entities: [], relations: [], evidence: [] });
    const stdout = [
      JSON.stringify({ type: "assistant.message", data: { content: "partial" } }),
      JSON.stringify({ type: "assistant.message", data: { content: graph } }),
      JSON.stringify({ type: "result", exitCode: 0 }),
    ].join("\n");

    expect(runner.parseOutput(stdout)).toBe(graph);
  });

  it("rejects a Copilot result event with a non-zero exit code", () => {
    const stdout = JSON.stringify({ type: "result", exitCode: 1 });

    expect(() => runner.parseOutput(stdout)).toThrow(LlmExecutionError);
  });

  it("rejects output without an assistant message", () => {
    expect(() => runner.parseOutput(JSON.stringify({ type: "result", exitCode: 0 })))
      .toThrow("Copilot CLI did not emit a final assistant message");
  });
});
