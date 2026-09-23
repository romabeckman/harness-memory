import { LlmAgentType } from "./llm-agent.js";

export const ALLOWED_ENTITY_TYPES = [
  "project",
  "system",
  "service",
  "api",
  "event",
  "library",
  "team",
  "adr",
  "feature",
  "spec",
  "document",
  "document_revision",
  "document_section",
  "rule",
] as const;

export type EntityType = (typeof ALLOWED_ENTITY_TYPES)[number];

export const ALLOWED_RELATION_TYPES = [
  "part_of",
  "owned_by",
  "provides",
  "consumes",
  "depends_on",
  "publishes",
  "subscribes_to",
  "implements",
  "references",
  "tested_by",
  "child_of",
  "defines",
  "applies_to",
  "supersedes",
] as const;

export type RelationType = (typeof ALLOWED_RELATION_TYPES)[number];

export const ALLOWED_PROVENANCE_KINDS = [
  "declared",
  "inferred",
  "observed",
  "manual",
] as const;

export type ProvenanceKind = (typeof ALLOWED_PROVENANCE_KINDS)[number];

export interface EntityFact {
  key: string;
  type: EntityType;
  name?: string;
  canonical_key?: string | null;
  metadata?: Record<string, unknown>;
}

export interface RelationFact {
  ref: string;
  source_entity_key: string;
  type: RelationType;
  target_entity_key: string;
  provenance: ProvenanceKind;
  metadata?: Record<string, unknown>;
}

export interface EvidenceFact {
  source: string;
  excerpt?: string;
  relation_ref?: string;
  metadata?: Record<string, unknown>;
}

export interface GraphDocument {
  schema_version: string;
  entities: EntityFact[];
  relations: RelationFact[];
  evidence: EvidenceFact[];
}

export interface PublishSnapshotOptions {
  repository: string;
  projectKey: string;
  environment: string;
  deploymentId: string;
  version: string;
  agent: LlmAgentType;
  model: string;
  effort: "low" | "medium" | "high" | "xhigh";
  baseRef?: string;
  headRef: string;
  dryRun: boolean;
  apiUrl?: string;
  token?: string;
  llmCommand?: string;
  timeout?: number;
  maxFiles?: number;
  maxBytes?: number;
  verbose?: boolean;
}

export interface PublicationResult {
  status: "ACTIVATED" | "ALREADY_PUBLISHED" | "DRY_RUN";
  publicationId?: string;
  snapshotId?: string;
  projectKey: string;
  environment: string;
  deploymentId: string;
  version: string;
  payloadSha256: string;
  counts?: {
    entities: number;
    relations: number;
    evidence: number;
  };
}
