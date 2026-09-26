import { describe, expect, it } from "vitest";
import { AgyCliRunner } from "../../../../src/infrastructure/llm/agy-cli-runner.js";

describe("AgyCliRunner", () => {
  const runner = new AgyCliRunner();

  it("builds non-interactive agy CLI arguments using model and effort when supplied", () => {
    expect(runner.buildArgs({ model: "Gemini 3.8 Flash (High)", effort: "high" })).toEqual([
      "--dangerously-skip-permissions",
      "--input-format",
      "text",
      "--output-format",
      "json",
      "--model",
      "Gemini 3.8 Flash (High)",
      "--effort",
      "high",
    ]);
  });

  it("omits --model and --effort when not provided", () => {
    expect(runner.buildArgs({ model: "", effort: "" as any })).toEqual([
      "--dangerously-skip-permissions",
      "--input-format",
      "text",
      "--output-format",
      "json",
    ]);
  });

  it("extracts graph JSON from agy response envelope", () => {
    const graph = JSON.stringify({ schema_version: "1.0", entities: [], relations: [], evidence: [] });

    expect(runner.parseOutput(JSON.stringify({ status: "SUCCESS", response: graph }))).toBe(graph);
  });

  it("accepts a raw graph document if emitted directly", () => {
    const graph = { schema_version: "1.0", entities: [], relations: [], evidence: [] };

    expect(runner.parseOutput(JSON.stringify(graph))).toBe(JSON.stringify(graph));
  });

  it("rejects an agy response envelope marked as ERROR", () => {
    expect(() =>
      runner.parseOutput(
        JSON.stringify({ status: "ERROR", error: "model not recognized", response: "" })
      )
    ).toThrow("AGY CLI returned an error: model not recognized");
  });

  it("rejects empty stdout", () => {
    expect(() => runner.parseOutput("   ")).toThrow("AGY CLI emitted empty stdout");
  });

  it("rejects an agy response missing response content", () => {
    expect(() =>
      runner.parseOutput(JSON.stringify({ status: "SUCCESS", response: "   " }))
    ).toThrow("AGY CLI response omitted final response text");
  });

  it("strips markdown code blocks from response", () => {
    const graph = JSON.stringify({ schema_version: "1.0", entities: [], relations: [], evidence: [] });
    const fenced = "```json\n" + graph + "\n```";

    expect(runner.parseOutput(JSON.stringify({ status: "SUCCESS", response: fenced }))).toBe(graph);
  });
});
