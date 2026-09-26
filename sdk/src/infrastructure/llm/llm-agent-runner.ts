import { LlmInvocationOptions } from "../../application/ports/llm-runner.port.js";
import { LlmAgentType } from "../../domain/llm-agent.js";

export type LlmAgentRunnerOptions = Pick<LlmInvocationOptions, "model" | "effort"> &
  Partial<Pick<LlmInvocationOptions, "timeoutSeconds">>;

export interface LlmAgentRunner {
  readonly type: LlmAgentType;
  readonly command: string;
  readonly promptTransport?: "stdin" | "argument";
  buildArgs(options: LlmAgentRunnerOptions, prompt?: string): string[];
  parseOutput(stdout: string): string;
}
