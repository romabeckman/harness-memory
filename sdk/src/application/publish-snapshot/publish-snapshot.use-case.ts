import type { PublicationResult, PublishSnapshotOptions } from "../../domain/contracts.js";
import type { GitContextCollectorPort } from "../ports/git-context-collector.port.js";
import type { GraphValidatorPort } from "../ports/graph-validator.port.js";
import type { PublicationClientPort } from "../ports/publication-client.port.js";
import type { MemoryWorkflowPort } from "../ports/memory-workflow.port.js";
import type { DocumentationDirectoryPort } from "../ports/documentation-directory.port.js";
import { ConfigurationError } from "../../domain/configuration-error.js";
import { CollectContextPhase } from "./phases/collect-context-phase.js";
import { RouteDocumentationPhase } from "./phases/route-documentation-phase.js";
import { PublishPhase } from "./phases/publish-phase.js";
import { ValidateGraphPhase } from "./phases/validate-graph-phase.js";
import { ValidateOptionsPhase } from "./phases/validate-options-phase.js";
import { ValidatePublicationTargetPhase } from "./phases/validate-publication-target-phase.js";
import type { PublicationProgressReporter } from "./phases/publication-phase-context.js";

export class PublishSnapshotUseCase {
  constructor(
    private readonly gitCollector: GitContextCollectorPort,
    private readonly graphValidator: GraphValidatorPort,
    private readonly publicationClient: PublicationClientPort,
    private readonly memoryWorkflow: MemoryWorkflowPort,
    private readonly documentationDirectory: DocumentationDirectoryPort,
  ) {}

  public async execute(
    options: PublishSnapshotOptions,
    onProgress?: PublicationProgressReporter,
  ): Promise<PublicationResult> {
    if (!this.memoryWorkflow || !this.documentationDirectory) {
      throw new ConfigurationError("Documented memory workflow and documentation directory are required");
    }
    const first = new ValidateOptionsPhase();
    const validation = new ValidateGraphPhase(this.graphValidator);
    validation.setNext(new PublishPhase(this.publicationClient));
    const collect = new CollectContextPhase(this.gitCollector);
    collect.setNext(new RouteDocumentationPhase(
      this.documentationDirectory, this.memoryWorkflow, validation,
    ));

    if (options.dryRun) {
      first.setNext(collect);
    } else {
      first.setNext(new ValidatePublicationTargetPhase(this.publicationClient))
        .setNext(collect);
    }
    return first.handle({ options, onProgress });
  }
}
