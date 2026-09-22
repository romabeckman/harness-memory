import { describe, expect, it } from "vitest";
import { CodexCliRunner } from "../../../../src/infrastructure/llm/codex-cli-runner.js";

describe("CodexCliRunner", () => {
  const runner = new CodexCliRunner();

  it("builds Codex CLI arguments using selected model and effort", () => {
    expect(runner.buildArgs({ model: "gpt-5", effort: "high" })).toEqual([
      "exec",
      "--json",
      "--model",
      "gpt-5",
      "--config",
      'model_reasoning_effort="high"',
      "-",
    ]);
  });

  it("extracts final graph JSON from Codex JSONL events", () => {
    const graph = JSON.stringify({ schema_version: "1.0", entities: [], relations: [], evidence: [] });
    const stdout = [
      JSON.stringify({ type: "item.completed", item: { type: "agent_message", text: graph } }),
      JSON.stringify({ type: "turn.completed" }),
    ].join("\n");

    expect(runner.parseOutput(stdout)).toBe(graph);
  });
});
