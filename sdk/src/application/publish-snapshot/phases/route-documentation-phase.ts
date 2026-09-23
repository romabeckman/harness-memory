import type { DocumentationDirectoryPort } from "../../ports/documentation-directory.port.js";
import type { MemoryWorkflowPort } from "../../ports/memory-workflow.port.js";
import { AbstractPublicationPhase } from "./abstract-publication-phase.js";
import { GenerateWithDocsPhase } from "./generate-with-docs-phase.js";
import { ConfigurationError } from "../../../domain/configuration-error.js";
import type { PublicationPhaseContext } from "./publication-phase-context.js";

export class RouteDocumentationPhase extends AbstractPublicationPhase {
  constructor(
    private readonly directory: DocumentationDirectoryPort,
    private readonly existing: MemoryWorkflowPort,
    private readonly downstream: AbstractPublicationPhase,
  ) { super(); }

  protected getProgressLabel(): string { return "Selecting documentation flow"; }

  protected execute(context: PublicationPhaseContext): void {
    if (!this.directory.exists(context.options.repository)) {
      throw new ConfigurationError("Documentation required: This project has no documentation in docs/. Please run the project-memory skill from https://github.com/romabeckman/harness-kit to generate docs/ before publishing to corporate memory.");
    }
    const generation = new GenerateWithDocsPhase(this.existing);
    generation.setNext(this.downstream);
    this.setNext(generation);
  }
}
