import { describe, expect, it } from "vitest";
import { ClaudeCliRunner } from "../../../../src/infrastructure/llm/claude-cli-runner.js";

describe("ClaudeCliRunner", () => {
  const runner = new ClaudeCliRunner();

  it("builds non-interactive Claude CLI arguments using selected model", () => {
    expect(runner.buildArgs({ model: "claude-sonnet", effort: "high" })).toEqual([
      "--print",
      "--output-format",
      "json",
      "--input-format",
      "text",
      "--model",
      "claude-sonnet",
      "--effort",
      "high",
    ]);
  });

  it("extracts graph JSON from Claude JSON result envelope", () => {
    const graph = JSON.stringify({ schema_version: "1.0", entities: [], relations: [], evidence: [] });

    expect(runner.parseOutput(JSON.stringify({ result: graph }))).toBe(graph);
  });

  it("rejects a Claude result envelope marked as an error", () => {
    expect(() => runner.parseOutput(JSON.stringify({ is_error: true, result: "hidden detail" }))).toThrow(
      "Claude CLI returned an error"
    );
  });
});
