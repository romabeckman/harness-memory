import { ConfigurationError } from "../../../domain/configuration-error.js";
import type { PublicationClientPort } from "../../ports/publication-client.port.js";
import { AbstractPublicationPhase } from "./abstract-publication-phase.js";
import type { PublicationPhaseContext } from "./publication-phase-context.js";

export class ValidatePublicationTargetPhase extends AbstractPublicationPhase {
  constructor(private readonly client: PublicationClientPort) { super(); }

  protected getProgressLabel(): string { return "Validating publication target"; }

  protected async execute(context: PublicationPhaseContext): Promise<void> {
    const { options, token } = context;
    if (options.dryRun) return;
    if (!options.apiUrl || !token) {
      throw new ConfigurationError("apiUrl and token are required for publication target validation");
    }
    context.resolvedTenantId = await this.client.validateTarget({
      apiUrl: options.apiUrl,
      token,
      tenantId: options.tenantId,
      projectKey: options.projectKey,
      environment: options.environment,
      deploymentId: options.deploymentId,
      version: options.version,
    });
  }
}
