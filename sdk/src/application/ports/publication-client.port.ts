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

export interface PublicationClientPort {
  publish(request: PublishRequest): Promise<PublicationResult>;
}
