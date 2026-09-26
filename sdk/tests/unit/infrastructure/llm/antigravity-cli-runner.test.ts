import { describe, expect, it } from "vitest";
import { LlmExecutionError } from "../../../../src/domain/llm-execution-error.js";
import { AntigravityCliRunner } from "../../../../src/infrastructure/llm/antigravity-cli-runner.js";

describe("AntigravityCliRunner", () => {
  const runner = new AntigravityCliRunner();

  it("builds non-interactive Antigravity CLI arguments", () => {
    expect(runner.buildArgs({ model: "gemini-2.5-pro", effort: "high" })).toEqual([
      "--model",
      "gemini-2.5-pro",
      "--effort",
      "high",
      "--output-format",
      "json",
      "--print-timeout",
      "601000ms",
      "--dangerously-skip-permissions",
    ]);
  });

  it("extracts graph JSON from Antigravity response output", () => {
    const graph = JSON.stringify({ schema_version: "1.0", entities: [], relations: [], evidence: [] });

    expect(runner.parseOutput(JSON.stringify({ status: "COMPLETED", response: graph }))).toBe(graph);
  });

  it("accepts a response when Antigravity reports a recoverable error status", () => {
    const graph = JSON.stringify({ schema_version: "1.0", entities: [], relations: [], evidence: [] });

    expect(runner.parseOutput(JSON.stringify({ status: "ERROR", response: graph }))).toBe(graph);
  });

  it("rejects failed Antigravity output", () => {
    expect(() => runner.parseOutput(JSON.stringify({ status: "FAILED", error: "model failed" })))
      .toThrow(LlmExecutionError);
  });

  it("rejects empty output", () => {
    expect(() => runner.parseOutput("  ")).toThrow("Antigravity CLI emitted empty stdout");
  });
});
