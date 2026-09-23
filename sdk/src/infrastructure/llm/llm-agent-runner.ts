import { LlmInvocationOptions } from "../../application/ports/llm-runner.port.js";
import { LlmAgentType } from "../../domain/llm-agent.js";

export interface LlmAgentRunner {
  readonly type: LlmAgentType;
  readonly command: string;
  buildArgs(options: Pick<LlmInvocationOptions, "model" | "effort">): string[];
  parseOutput(stdout: string): string;
}
