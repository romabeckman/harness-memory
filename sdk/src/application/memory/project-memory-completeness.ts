import type { CollectedFile } from "../ports/git-context-collector.port.js";

export class ProjectMemoryCompleteness {
  public isComplete(files: CollectedFile[]): boolean {
    const paths = new Set(files.map(file => file.path));
    const required = ["docs/.graph.json", "docs/.digest.md", "docs/README.md",
      "docs/adr/ARCHITECTURE.md", "docs/adr/TESTS.md"];
    if (!required.every(path => paths.has(path))) return false;
    const graphDocuments = files.filter(file => /^docs\/(adr|feature)\/.*\.md$/.test(file.path));
    if (!graphDocuments.some(file => file.path.startsWith("docs/feature/"))) return false;
    return graphDocuments.every(file => /^---\r?\n/.test(file.content) &&
      /^node_id:\s*["']?[\w-]+:[\w-]+["']?\s*$/m.test(file.content) &&
      (!file.path.startsWith("docs/feature/") || /```graph\s*\r?\n\s*\{/.test(file.content)));
  }
}
