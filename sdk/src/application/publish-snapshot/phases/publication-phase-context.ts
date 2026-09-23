import type { PublicationResult, PublishSnapshotOptions } from "../../../domain/contracts.js";
import type { RepositoryContext } from "../../ports/git-context-collector.port.js";
import type { ValidatedGraph } from "../../ports/graph-validator.port.js";

export interface PublicationPhaseContext {
  options: PublishSnapshotOptions;
  onProgress?: PublicationProgressReporter;
  token?: string;
  resolvedTenantId?: string;
  repositoryContext?: RepositoryContext;
  rawDocument?: unknown;
  validatedGraph?: ValidatedGraph;
  noChanges?: boolean;
}

export interface PublicationProgressEvent {
  phase: string;
  state: "started" | "completed" | "failed";
}

export type PublicationProgressReporter = (event: PublicationProgressEvent) => void;

export type PhaseOutcome = PublicationResult | void;
