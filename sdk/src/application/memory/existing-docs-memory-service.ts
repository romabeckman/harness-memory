import type { GraphDocument, PublishSnapshotOptions } from "../../domain/contracts.js";
import { GraphValidationError } from "../../domain/graph-validation-error.js";
import type { DocsStorePort } from "../ports/docs-store.port.js";
import type { RepositoryContext } from "../ports/git-context-collector.port.js";
import type { MemoryWorkflowPort } from "../ports/memory-workflow.port.js";
import { ProjectMemoryCompleteness } from "./project-memory-completeness.js";

export class ExistingDocsMemoryService implements MemoryWorkflowPort {
  constructor(
    private readonly workflow: MemoryWorkflowPort,
    private readonly docs: DocsStorePort,
    private readonly completeness = new ProjectMemoryCompleteness(),
  ) {}

  public async run(options: PublishSnapshotOptions, context: RepositoryContext): Promise<GraphDocument> {
    if (!this.completeness.isComplete(this.docs.read(options.repository))) {
      throw new GraphValidationError("Existing documentation is incomplete");
    }
    return this.workflow.run(options, context);
  }
}
