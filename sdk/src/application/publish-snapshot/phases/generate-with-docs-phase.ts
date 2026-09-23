import type { MemoryWorkflowPort } from "../../ports/memory-workflow.port.js";
import { AbstractPublicationPhase } from "./abstract-publication-phase.js";
import type { PublicationPhaseContext } from "./publication-phase-context.js";

export class GenerateWithDocsPhase extends AbstractPublicationPhase {
  constructor(private readonly workflow: MemoryWorkflowPort) { super(); }

  protected getProgressLabel(): string {
    return "Fetching previous snapshot and building knowledge graph";
  }

  protected async execute(context: PublicationPhaseContext): Promise<void> {
    if (!context.repositoryContext) throw new Error("Repository context is required before document generation");
    context.rawDocument = await this.workflow.run(
      { ...context.options, token: context.token }, context.repositoryContext,
    );
  }
}
