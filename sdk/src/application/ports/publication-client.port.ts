import { PublicationResult } from "../../domain/contracts.js";
import { ValidatedGraph } from "./graph-validator.port.js";

export interface PublishRequest {
  apiUrl: string;
  token: string;
  projectKey: string;
  environment: string;
  deploymentId: string;
  version: string;
  graph: ValidatedGraph;
}

export type PublicationTargetRequest = Pick<
  PublishRequest,
  "apiUrl" | "token" | "projectKey" | "environment" | "deploymentId" | "version"
>;

export interface PublicationClientPort {
  validateTarget(request: PublicationTargetRequest): Promise<void>;
  publish(request: PublishRequest): Promise<PublicationResult>;
}
