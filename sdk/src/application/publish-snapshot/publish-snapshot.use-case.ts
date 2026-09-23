import type { PublicationResult, PublishSnapshotOptions } from "../../domain/contracts.js";
import type { GitContextCollectorPort } from "../ports/git-context-collector.port.js";
import type { LlmRunnerPort } from "../ports/llm-runner.port.js";
import type { GraphValidatorPort } from "../ports/graph-validator.port.js";
import type { PublicationClientPort } from "../ports/publication-client.port.js";
import type { MemoryWorkflowPort } from "../ports/memory-workflow.port.js";
import { CollectContextPhase } from "./phases/collect-context-phase.js";
import { GenerateDocumentPhase } from "./phases/generate-document-phase.js";
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
  ) {}

  public async execute(
    options: PublishSnapshotOptions,
    onProgress?: PublicationProgressReporter,
  ): Promise<PublicationResult> {
    const first = new ValidateOptionsPhase();
    first.setNext(new CollectContextPhase(this.gitCollector))
      .setNext(new GenerateDocumentPhase(this.llmRunner, this.memoryWorkflow))
      .setNext(new ValidateGraphPhase(this.graphValidator))
      .setNext(new PublishPhase(this.publicationClient));
    return first.handle({ options, onProgress });
  }
}
