import { existsSync, lstatSync, realpathSync } from "node:fs";
import { join } from "node:path";
import type { DocumentationDirectoryPort } from "../../application/ports/documentation-directory.port.js";
import { ContextCollectionError } from "../../domain/context-collection-error.js";

export class LocalDocsDirectory implements DocumentationDirectoryPort {
  public exists(repository: string): boolean {
    const path = join(realpathSync(repository), "docs");
    if (!existsSync(path)) return false;
    const stat = lstatSync(path);
    if (!stat.isDirectory() || stat.isSymbolicLink()) {
      throw new ContextCollectionError("docs must be a regular directory");
    }
    return true;
  }
}
