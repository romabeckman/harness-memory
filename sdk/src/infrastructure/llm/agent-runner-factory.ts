import { LlmExecutionError } from "../../domain/llm-execution-error.js";
import { AntigravityCliRunner } from "./antigravity-cli-runner.js";
import { AgyCliRunner } from "./agy-cli-runner.js";
import { ClaudeCliRunner } from "./claude-cli-runner.js";
import { CopilotCliRunner } from "./copilot-cli-runner.js";
import { CodexCliRunner } from "./codex-cli-runner.js";
import { LlmAgentRunner } from "./llm-agent-runner.js";

export class AgentRunnerFactory {
  private readonly runners = new Map<string, LlmAgentRunner>();

  constructor(runners: LlmAgentRunner[] = [
    new CodexCliRunner(),
    new ClaudeCliRunner(),
    new AntigravityCliRunner(),
    new CopilotCliRunner(),
    new AgyCliRunner(),
  ]) {
    for (const runner of runners) this.register(runner);
  }


  public register(runner: LlmAgentRunner): void {
    if (this.runners.has(runner.type)) {
      throw new LlmExecutionError(`LLM agent '${runner.type}' is already registered`);
    }
    this.runners.set(runner.type, runner);
  }

  public create(agent: string): LlmAgentRunner {
    const runner = this.runners.get(agent);
    if (!runner) {
      throw new LlmExecutionError(`Unsupported LLM agent '${agent}'`);
    }
    return runner;
  }
}
