import { existsSync, lstatSync, mkdirSync, mkdtempSync, realpathSync, rmdirSync, rmSync } from "node:fs";
import { join } from "node:path";
import type { TemporaryDocsWorkspacePort } from "../../application/ports/temporary-docs-workspace.port.js";
import { ContextCollectionError } from "../../domain/context-collection-error.js";

export class LocalTemporaryDocsWorkspace implements TemporaryDocsWorkspacePort {
  private readonly owned = new Map<string, { parent: string; createdParent: boolean }>();

  public create(repository: string): string {
    const parent = join(realpathSync(repository), ".docs");
    const createdParent = !existsSync(parent);
    if (createdParent) mkdirSync(parent);
    const stat = lstatSync(parent);
    if (!stat.isDirectory() || stat.isSymbolicLink()) {
      throw new ContextCollectionError(".docs must be a regular directory");
    }
    const workspace = mkdtempSync(join(parent, "bootstrap-"));
    this.owned.set(workspace, { parent, createdParent });
    return workspace;
  }

  public cleanup(workspace: string): void {
    const owned = this.owned.get(workspace);
    if (!owned) throw new ContextCollectionError("Temporary documentation workspace is not owned by this process");
    this.owned.delete(workspace);
    rmSync(workspace, { recursive: true, force: true });
    if (owned.createdParent) {
      try { rmdirSync(owned.parent); }
      catch (error: any) { if (error.code !== "ENOTEMPTY" && error.code !== "ENOENT") throw error; }
    }
  }
}
