import type { GraphDocument, PublishSnapshotOptions } from "../../domain/contracts.js";
import { GraphValidationError } from "../../domain/graph-validation-error.js";
import type { DocsStorePort } from "../ports/docs-store.port.js";
import type { RepositoryContext } from "../ports/git-context-collector.port.js";
import type { MemoryWorkflowPort } from "../ports/memory-workflow.port.js";
import type { TemporaryDocsWorkspacePort } from "../ports/temporary-docs-workspace.port.js";
import { ProjectMemoryCompleteness } from "./project-memory-completeness.js";

export class MissingDocsMemoryService implements MemoryWorkflowPort {
  constructor(
    private readonly bootstrap: MemoryWorkflowPort,
    private readonly existing: MemoryWorkflowPort,
    private readonly docs: DocsStorePort,
    private readonly workspace: TemporaryDocsWorkspacePort,
    private readonly completeness = new ProjectMemoryCompleteness(),
    private readonly debug?: (message: string) => void,
  ) {}

  public async run(options: PublishSnapshotOptions, context: RepositoryContext): Promise<GraphDocument> {
    const workspace = this.workspace.create(options.repository);
    const stagedOptions = { ...options, repository: workspace, dryRun: true };
    try {
      this.debug?.("Memory: mapping architecture and features for documentation bootstrap");
      const generated = await this.bootstrap.run(stagedOptions, context);
      this.docs.write(workspace, generated, []);
      const stagedFiles = this.docs.read(workspace);
      if (!this.completeness.isComplete(stagedFiles)) {
        throw new GraphValidationError("Bootstrap documentation is incomplete");
      }
      this.debug?.(`Memory: staged ${stagedFiles.length} documents under .docs/; processing existing-docs flow`);
      const graph = await this.existing.run(stagedOptions, context);
      if (!options.dryRun) {
        this.docs.write(options.repository, graph, []);
        this.debug?.("Memory: promoted validated documents to docs/");
      }
      return graph;
    } finally {
      this.workspace.cleanup(workspace);
      this.debug?.("Memory: removed temporary .docs/ workspace");
    }
  }
}
