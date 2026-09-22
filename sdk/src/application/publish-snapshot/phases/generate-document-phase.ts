import type { LlmRunnerPort } from "../../ports/llm-runner.port.js";
import type { MemoryWorkflowPort } from "../../ports/memory-workflow.port.js";
import { AbstractPublicationPhase } from "./abstract-publication-phase.js";
import type { PublicationPhaseContext } from "./publication-phase-context.js";

export class GenerateDocumentPhase extends AbstractPublicationPhase {
  constructor(
    private readonly runner: LlmRunnerPort,
    private readonly memoryWorkflow?: MemoryWorkflowPort,
  ) { super(); }

  protected async execute(context: PublicationPhaseContext): Promise<void> {
    const { options, repositoryContext } = context;
    if (!repositoryContext) throw new Error("Repository context is required before document generation");
    context.rawDocument = this.memoryWorkflow
      ? await this.memoryWorkflow.run({ ...options, token: context.token }, repositoryContext)
      : await this.runner.run({
        agent: options.agent,
        model: options.model,
        effort: options.effort,
        llmCommand: options.llmCommand,
        timeoutSeconds: options.timeout ?? 600,
        projectKey: options.projectKey,
        environment: options.environment,
        context: repositoryContext,
      });
  }
}
