import type { DocumentationDirectoryPort } from "../../ports/documentation-directory.port.js";
import type { MemoryWorkflowPort } from "../../ports/memory-workflow.port.js";
import { AbstractPublicationPhase } from "./abstract-publication-phase.js";
import { GenerateWithDocsPhase } from "./generate-with-docs-phase.js";
import { GenerateWithoutDocsPhase } from "./generate-without-docs-phase.js";
import type { PublicationPhaseContext } from "./publication-phase-context.js";

export class RouteDocumentationPhase extends AbstractPublicationPhase {
  constructor(
    private readonly directory: DocumentationDirectoryPort,
    private readonly existing: MemoryWorkflowPort,
    private readonly missing: MemoryWorkflowPort,
    private readonly downstream: AbstractPublicationPhase,
  ) { super(); }

  protected getProgressLabel(): string { return "Selecting documentation flow"; }

  protected execute(context: PublicationPhaseContext): void {
    const generation = this.directory.exists(context.options.repository)
      ? new GenerateWithDocsPhase(this.existing)
      : new GenerateWithoutDocsPhase(this.missing);
    generation.setNext(this.downstream);
    this.setNext(generation);
  }
}
