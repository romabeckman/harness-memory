import { GraphDocument, PublishSnapshotOptions } from "../../domain/contracts.js";
import { RepositoryContext } from "./git-context-collector.port.js";

export interface MemoryWorkflowPort {
  run(options: PublishSnapshotOptions, context: RepositoryContext): Promise<GraphDocument>;
}
