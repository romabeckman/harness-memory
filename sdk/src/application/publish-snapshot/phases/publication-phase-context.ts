import type { PublicationResult, PublishSnapshotOptions } from "../../../domain/contracts.js";
import type { RepositoryContext } from "../../ports/git-context-collector.port.js";
import type { ValidatedGraph } from "../../ports/graph-validator.port.js";

export interface PublicationPhaseContext {
  options: PublishSnapshotOptions;
  token?: string;
  repositoryContext?: RepositoryContext;
  rawDocument?: unknown;
  validatedGraph?: ValidatedGraph;
}

export type PhaseOutcome = PublicationResult | void;
