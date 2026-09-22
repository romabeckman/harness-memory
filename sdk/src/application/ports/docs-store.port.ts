import { GraphDocument } from "../../domain/contracts.js";
import { CollectedFile } from "./git-context-collector.port.js";

export interface DocsStorePort {
  read(repository: string): CollectedFile[];
  write(repository: string, graph: GraphDocument, originals: CollectedFile[]): void;
}
