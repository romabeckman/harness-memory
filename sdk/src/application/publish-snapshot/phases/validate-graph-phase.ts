import type { GraphValidatorPort } from "../../ports/graph-validator.port.js";
import { AbstractPublicationPhase } from "./abstract-publication-phase.js";
import type { PublicationPhaseContext } from "./publication-phase-context.js";
import type { PublicationResult } from "../../../domain/contracts.js";

export class ValidateGraphPhase extends AbstractPublicationPhase {
  constructor(private readonly validator: GraphValidatorPort) { super(); }

  protected getProgressLabel(): string { return "Validating knowledge graph"; }

  protected execute(context: PublicationPhaseContext): PublicationResult | void {
    if (!context.rawDocument) throw new Error("Document is required before graph validation");
    context.validatedGraph = this.validator.validateAndCanonicalize(context.rawDocument);
    if (context.noChanges && !context.options.dryRun) {
      return {
        status: "NO_CHANGES",
        projectKey: context.options.projectKey,
        environment: context.options.environment,
        deploymentId: context.options.deploymentId,
        version: context.options.version,
        payloadSha256: context.validatedGraph.sha256,
        counts: context.validatedGraph.counts,
        message: "No documentation changes detected; no snapshot was created.",
      };
    }
  }
}
