import type { GraphValidatorPort } from "../../ports/graph-validator.port.js";
import { AbstractPublicationPhase } from "./abstract-publication-phase.js";
import type { PublicationPhaseContext } from "./publication-phase-context.js";

export class ValidateGraphPhase extends AbstractPublicationPhase {
  constructor(private readonly validator: GraphValidatorPort) { super(); }

  protected getProgressLabel(): string { return "Validating knowledge graph"; }

  protected execute(context: PublicationPhaseContext): void {
    if (!context.rawDocument) throw new Error("Document is required before graph validation");
    context.validatedGraph = this.validator.validateAndCanonicalize(context.rawDocument);
  }
}
