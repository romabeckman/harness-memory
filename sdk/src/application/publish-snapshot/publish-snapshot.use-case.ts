import type { PublicationResult, PublishSnapshotOptions } from "../../domain/contracts.js";
import type { GitContextCollectorPort } from "../ports/git-context-collector.port.js";
import type { LlmRunnerPort } from "../ports/llm-runner.port.js";
import type { GraphValidatorPort } from "../ports/graph-validator.port.js";
import type { PublicationClientPort } from "../ports/publication-client.port.js";
import type { MemoryWorkflowPort } from "../ports/memory-workflow.port.js";
import type { DocumentationDirectoryPort } from "../ports/documentation-directory.port.js";
import { CollectContextPhase } from "./phases/collect-context-phase.js";
import { GenerateDocumentPhase } from "./phases/generate-document-phase.js";
import { RouteDocumentationPhase } from "./phases/route-documentation-phase.js";
import { PublishPhase } from "./phases/publish-phase.js";
import { ValidateGraphPhase } from "./phases/validate-graph-phase.js";
import { ValidateOptionsPhase } from "./phases/validate-options-phase.js";
import type { PublicationProgressReporter } from "./phases/publication-phase-context.js";

export class PublishSnapshotUseCase {
  constructor(
    private readonly gitCollector: GitContextCollectorPort,
    private readonly llmRunner: LlmRunnerPort,
    private readonly graphValidator: GraphValidatorPort,
    private readonly publicationClient: PublicationClientPort,
    private readonly memoryWorkflow?: MemoryWorkflowPort,
    private readonly missingDocsWorkflow?: MemoryWorkflowPort,
    private readonly documentationDirectory?: DocumentationDirectoryPort,
  ) {}

  public async execute(
    options: PublishSnapshotOptions,
    onProgress?: PublicationProgressReporter,
  ): Promise<PublicationResult> {
    const first = new ValidateOptionsPhase();
    const validation = new ValidateGraphPhase(this.graphValidator);
    validation.setNext(new PublishPhase(this.publicationClient));
    if (this.memoryWorkflow && this.missingDocsWorkflow && this.documentationDirectory) {
      first.setNext(new CollectContextPhase(this.gitCollector))
        .setNext(new RouteDocumentationPhase(
          this.documentationDirectory, this.memoryWorkflow, this.missingDocsWorkflow, validation,
        ));
    } else {
      first.setNext(new CollectContextPhase(this.gitCollector))
        .setNext(new GenerateDocumentPhase(this.llmRunner, this.memoryWorkflow))
        .setNext(validation);
    }
    return first.handle({ options, onProgress });
  }
}
