import { GraphDocument } from "../../domain/contracts.js";
import { LlmAgentType } from "../../domain/llm-agent.js";
import { RepositoryContext } from "./git-context-collector.port.js";

export interface LlmInvocationOptions {
  agent: LlmAgentType;
  model: string;
  effort: "low" | "medium" | "high" | "xhigh";
  llmCommand?: string;
  timeoutSeconds: number;
  projectKey: string;
  environment: string;
  context: RepositoryContext;
  instruction?: string;
  baselineGraph?: GraphDocument;
  documentationGraph?: GraphDocument;
}

export interface LlmRunnerPort {
  run(options: LlmInvocationOptions): Promise<GraphDocument>;
}
