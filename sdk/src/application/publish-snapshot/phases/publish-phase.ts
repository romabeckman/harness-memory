import { ConfigurationError } from "../../../domain/configuration-error.js";
import type { PublicationResult } from "../../../domain/contracts.js";
import type { PublicationClientPort } from "../../ports/publication-client.port.js";
import { AbstractPublicationPhase } from "./abstract-publication-phase.js";
import type { PublicationPhaseContext } from "./publication-phase-context.js";

export class PublishPhase extends AbstractPublicationPhase {
  constructor(private readonly client: PublicationClientPort) { super(); }

  protected getProgressLabel(context: PublicationPhaseContext): string {
    return context.options.dryRun ? "Preparing dry-run result" : "Publishing snapshot";
  }

  protected async execute(context: PublicationPhaseContext): Promise<PublicationResult> {
    const { options, validatedGraph, token } = context;
    if (!validatedGraph) throw new Error("Validated graph is required before publication");
    if (options.dryRun) {
      return {
        status: "DRY_RUN",
        projectKey: options.projectKey,
        environment: options.environment,
        deploymentId: options.deploymentId,
        version: options.version,
        payloadSha256: validatedGraph.sha256,
        counts: validatedGraph.counts,
      };
    }
    if (!options.apiUrl || !token) {
      throw new ConfigurationError("apiUrl and token are required when dryRun is false");
    }
    return this.client.publish({
      apiUrl: options.apiUrl,
      token,
      projectKey: options.projectKey,
      environment: options.environment,
      deploymentId: options.deploymentId,
      version: options.version,
      graph: validatedGraph,
    });
  }
}
