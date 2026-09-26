import { describe, expect, it } from "vitest";
import { AgentRunnerFactory } from "../../../../src/infrastructure/llm/agent-runner-factory.js";
import { AntigravityCliRunner } from "../../../../src/infrastructure/llm/antigravity-cli-runner.js";
import { ClaudeCliRunner } from "../../../../src/infrastructure/llm/claude-cli-runner.js";
import { CopilotCliRunner } from "../../../../src/infrastructure/llm/copilot-cli-runner.js";
import { CodexCliRunner } from "../../../../src/infrastructure/llm/codex-cli-runner.js";

describe("AgentRunnerFactory", () => {
  const factory = new AgentRunnerFactory();

  it("creates the Codex runner by runner id", () => {
    expect(factory.create("codex-cli")).toBeInstanceOf(CodexCliRunner);
  });

  it("creates the Claude runner by runner id", () => {
    expect(factory.create("claude-cli")).toBeInstanceOf(ClaudeCliRunner);
  });

  it("creates the Antigravity runner by runner id", () => {
    expect(factory.create("antigravity-cli")).toBeInstanceOf(AntigravityCliRunner);
  });

  it("creates the Copilot runner by runner id", () => {
    expect(factory.create("copilot-cli")).toBeInstanceOf(CopilotCliRunner);
  });

  it("rejects runner ids without a registered adapter", () => {
    expect(() => factory.create("unknown-cli")).toThrow("Unsupported LLM agent");
  });
});
