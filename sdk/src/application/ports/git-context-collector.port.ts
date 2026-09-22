export interface CollectedFile {
  path: string;
  content: string;
  sha256: string;
}

export interface GitDiffEntry {
  status: "added" | "modified" | "deleted" | "renamed";
  oldPath?: string;
  newPath?: string;
}

export interface RepositoryContext {
  commitSha: string;
  baseRef?: string;
  headRef: string;
  files: CollectedFile[];
  diffs: GitDiffEntry[];
}

export interface GitContextCollectorPort {
  collect(options: {
    repository: string;
    baseRef?: string;
    headRef: string;
    maxFiles: number;
    maxBytes: number;
  }): Promise<RepositoryContext>;
}
