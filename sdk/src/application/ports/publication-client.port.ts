import { PublicationResult } from "../../domain/contracts.js";
import { ValidatedGraph } from "./graph-validator.port.js";

export interface PublishRequest {
  apiUrl: string;
  token: string;
  tenantId?: string;
  projectKey: string;
  environment: string;
  deploymentId: string;
  version: string;
  expectedCurrentSnapshotId?: string;
  graph: ValidatedGraph;
}

export type PublicationTargetRequest = Pick<
  PublishRequest,
  "apiUrl" | "token" | "tenantId" | "projectKey" | "environment" | "deploymentId" | "version"
>;

export interface PublicationClientPort {
  validateTarget(request: PublicationTargetRequest): Promise<string | {
    tenantId: string;
    expectedCurrentSnapshotId: string;
  }>;
  publish(request: PublishRequest): Promise<PublicationResult>;
}
