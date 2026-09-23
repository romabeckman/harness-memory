import { ConfigurationError } from "../../../domain/configuration-error.js";
import { isLlmAgentType } from "../../../domain/llm-agent.js";
import { AbstractPublicationPhase } from "./abstract-publication-phase.js";
import type { PublicationPhaseContext } from "./publication-phase-context.js";

export class ValidateOptionsPhase extends AbstractPublicationPhase {
  protected getProgressLabel(): string { return "Checking publication settings"; }

  protected execute(context: PublicationPhaseContext): void {
    const { options } = context;
    for (const field of ["projectKey", "environment", "deploymentId", "version", "model"] as const) {
      if (!options[field]?.trim()) throw new ConfigurationError(`${field} is required`);
    }
    if (!options.effort || !["low", "medium", "high", "xhigh"].includes(options.effort)) {
      throw new ConfigurationError("effort must be one of: low, medium, high, xhigh");
    }
    if (!options.agent) throw new ConfigurationError("agent is required");
    if (!isLlmAgentType(options.agent)) {
      throw new ConfigurationError(`agent must be one of: codex-cli, claude-cli; received '${options.agent}'`);
    }
    context.token = options.token || process.env.HARNESS_MEMORY_API_KEY;
  }
}
