import type { GitContextCollectorPort } from "../../ports/git-context-collector.port.js";
import { AbstractPublicationPhase } from "./abstract-publication-phase.js";
import type { PublicationPhaseContext } from "./publication-phase-context.js";

export class CollectContextPhase extends AbstractPublicationPhase {
  constructor(private readonly collector: GitContextCollectorPort) { super(); }

  protected async execute(context: PublicationPhaseContext): Promise<void> {
    const { options } = context;
    context.repositoryContext = await this.collector.collect({
      repository: options.repository,
      baseRef: options.baseRef,
      headRef: options.headRef || "HEAD",
      maxFiles: options.maxFiles ?? 2000,
      maxBytes: options.maxBytes ?? 10485760,
    });
  }
}
