import { GraphDocument } from "../../domain/contracts.js";
import { RepositoryContext } from "./git-context-collector.port.js";

export interface LlmInvocationOptions {
  model: string;
  effort: "low" | "medium" | "high" | "xhigh";
  llmCommand: string;
  timeoutSeconds: number;
  projectKey: string;
  environment: string;
  context: RepositoryContext;
}

export interface LlmRunnerPort {
  run(options: LlmInvocationOptions): Promise<GraphDocument>;
}
