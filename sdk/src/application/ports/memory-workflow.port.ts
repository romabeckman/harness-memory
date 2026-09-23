import { GraphDocument, PublishSnapshotOptions } from "../../domain/contracts.js";
import { RepositoryContext } from "./git-context-collector.port.js";

export type MemoryWorkflowOutcome =
  | { status: "READY"; graph: GraphDocument }
  | { status: "NO_CHANGES"; graph: GraphDocument };

export interface MemoryWorkflowPort {
  run(options: PublishSnapshotOptions, context: RepositoryContext): Promise<MemoryWorkflowOutcome>;
}
