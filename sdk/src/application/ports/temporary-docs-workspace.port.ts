export interface TemporaryDocsWorkspacePort {
  create(repository: string): string;
  cleanup(workspace: string): void;
}
