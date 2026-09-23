import { CollectedFile } from "./git-context-collector.port.js";

export interface DocsStorePort {
  read(repository: string): CollectedFile[];
}
