import { GraphDocument } from "../../domain/contracts.js";

export interface PublicationBaselinePort {
  load(apiUrl: string, token: string, projectKey: string, environment: string): Promise<GraphDocument | undefined>;
}
