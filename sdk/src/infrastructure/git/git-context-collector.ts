import { execFile } from "node:child_process";
import { createHash } from "node:crypto";
import { lstatSync, readFileSync, realpathSync, statSync } from "node:fs";
import { isAbsolute, normalize, relative, resolve } from "node:path";
import { promisify } from "node:util";
import {
  CollectedFile,
  GitContextCollectorPort,
  GitDiffEntry,
  RepositoryContext,
} from "../../application/ports/git-context-collector.port.js";
import { ContextCollectionError } from "../../domain/context-collection-error.js";

const pExecFile = promisify(execFile);

const EXCLUDED_DIR_PATTERNS = [
  /^\.git(\/|\\|$)/,
  /^node_modules(\/|\\|$)/,
  /^dist(\/|\\|$)/,
  /^build(\/|\\|$)/,
  /^coverage(\/|\\|$)/,
  /^venv(\/|\\|$)/,
  /^\.venv(\/|\\|$)/,
];

const EXCLUDED_FILE_PATTERNS = [
  /\.pem$/i,
  /\.key$/i,
  /\.pkcs12$/i,
  /\.pfx$/i,
  /id_rsa/i,
  /^\.env/i,
  /\.secret/i,
  /\.credential/i,
];

export interface GitContextCollectorDeps {
  lstatSync?: typeof lstatSync;
  realpathSync?: typeof realpathSync;
  statSync?: typeof statSync;
  readFileSync?: typeof readFileSync;
}

export class GitContextCollector implements GitContextCollectorPort {
  private readonly _lstatSync: typeof lstatSync;
  private readonly _realpathSync: typeof realpathSync;
  private readonly _statSync: typeof statSync;
  private readonly _readFileSync: typeof readFileSync;

  constructor(deps?: GitContextCollectorDeps) {
    this._lstatSync = deps?.lstatSync ?? lstatSync;
    this._realpathSync = deps?.realpathSync ?? realpathSync;
    this._statSync = deps?.statSync ?? statSync;
    this._readFileSync = deps?.readFileSync ?? readFileSync;
  }

  public async collect(options: {
    repository: string;
    baseRef?: string;
    headRef: string;
    maxFiles: number;
    maxBytes: number;
  }): Promise<RepositoryContext> {
    const resolvedRepoPath = resolve(options.repository);
    let repoPath: string;
    try {
      repoPath = this._realpathSync(resolvedRepoPath);
    } catch {
      repoPath = resolvedRepoPath;
    }

    // Verify it is a valid git repository
    try {
      const { stdout } = await pExecFile(
        "git",
        ["rev-parse", "--is-inside-work-tree"],
        { cwd: repoPath }
      );
      if (stdout.trim() !== "true") {
        throw new ContextCollectionError(
          `Directory '${repoPath}' is not a git work tree`
        );
      }
    } catch (err: any) {
      if (err instanceof ContextCollectionError) throw err;
      throw new ContextCollectionError(
        `Failed to verify git repository at '${repoPath}': ${err.message}`
      );
    }

    // Resolve commit SHA of headRef
    let commitSha: string;
    try {
      const { stdout } = await pExecFile(
        "git",
        ["rev-parse", options.headRef || "HEAD"],
        { cwd: repoPath }
      );
      commitSha = stdout.trim();
    } catch (err: any) {
      throw new ContextCollectionError(
        `Invalid git head-ref '${options.headRef}': ${err.message}`
      );
    }

    // Collect diffs if baseRef is specified
    const diffs: GitDiffEntry[] = [];
    if (options.baseRef && options.baseRef.trim()) {
      try {
        const { stdout } = await pExecFile(
          "git",
          [
            "diff",
            "--name-status",
            `${options.baseRef}..${options.headRef || "HEAD"}`,
          ],
          { cwd: repoPath }
        );
        const lines = stdout.split("\n").filter((l) => l.trim().length > 0);
        for (const line of lines) {
          const parts = line.split("\t");
          const statusCode = parts[0]?.trim()[0];
          if (statusCode === "A") {
            diffs.push({ status: "added", newPath: parts[1] });
          } else if (statusCode === "M") {
            diffs.push({ status: "modified", newPath: parts[1] });
          } else if (statusCode === "D") {
            diffs.push({ status: "deleted", oldPath: parts[1] });
          } else if (statusCode === "R") {
            diffs.push({ status: "renamed", oldPath: parts[1], newPath: parts[2] });
          }
        }
      } catch (err: any) {
        throw new ContextCollectionError(
          `Failed to compute git diff between '${options.baseRef}' and '${options.headRef}': ${err.message}`
        );
      }
    }

    // List tracked files
    let trackedFiles: string[];
    try {
      const { stdout } = await pExecFile("git", ["ls-files"], {
        cwd: repoPath,
        maxBuffer: 10 * 1024 * 1024,
      });
      trackedFiles = stdout
        .split("\n")
        .map((f) => f.trim())
        .filter((f) => f.length > 0);
    } catch (err: any) {
      throw new ContextCollectionError(
        `Failed to list git tracked files: ${err.message}`
      );
    }

    // Filter, sort, and collect files
    const normalizedFiles = trackedFiles
      .map((f) => f.replace(/\\/g, "/"))
      .filter((filePath) => {
        if (EXCLUDED_DIR_PATTERNS.some((p) => p.test(filePath))) {
          return false;
        }
        const fileName = filePath.split("/").pop() || "";
        if (EXCLUDED_FILE_PATTERNS.some((p) => p.test(fileName))) {
          return false;
        }
        return true;
      })
      .sort((a, b) => a.localeCompare(b));

    if (normalizedFiles.length > options.maxFiles) {
      throw new ContextCollectionError(
        `File count (${normalizedFiles.length}) exceeds maxFiles limit of ${options.maxFiles}`
      );
    }

    const collected: CollectedFile[] = [];
    let totalBytes = 0;

    for (const relPath of normalizedFiles) {
      const fullPath = resolve(repoPath, relPath);

      // Path traversal check
      const relToRoot = relative(repoPath, fullPath);
      if (relToRoot.startsWith("..") || isAbsolute(relToRoot)) {
        throw new ContextCollectionError(`Path escape detected: '${relPath}'`);
      }

      let lstat;
      try {
        lstat = this._lstatSync(fullPath);
      } catch {
        continue; // file might be deleted in working tree
      }

      let realPath: string;
      try {
        realPath = this._realpathSync(fullPath);
      } catch (err: any) {
        throw new ContextCollectionError(
          `Failed to resolve real path for '${relPath}': ${err.message}`
        );
      }

      // Symlink escape check: ensure realPath is inside repoPath
      const realRelToRoot = relative(repoPath, realPath);
      if (realRelToRoot.startsWith("..") || isAbsolute(realRelToRoot)) {
        throw new ContextCollectionError(
          `Symlink escape detected: '${relPath}' points outside repository to '${realPath}'`
        );
      }

      let stat;
      try {
        stat = this._statSync(realPath);
      } catch {
        continue;
      }
      if (!stat.isFile()) continue;

      // Check file size against budget BEFORE reading into memory (OOM / heap exhaustion shield)
      if (stat.size > options.maxBytes || totalBytes + stat.size > options.maxBytes) {
        throw new ContextCollectionError(
          `Total context bytes (${totalBytes + stat.size}) exceeds maxBytes limit of ${options.maxBytes}`
        );
      }

      let buffer: Buffer;
      try {
        buffer = this._readFileSync(realPath);
      } catch (err: any) {
        throw new ContextCollectionError(
          `Failed to read file '${relPath}': ${err.message}`
        );
      }

      // Check for binary file (contains null byte in first 8000 bytes)
      const sample = buffer.subarray(0, 8000);
      if (sample.includes(0)) {
        continue; // skip binary
      }

      // Normalize line endings
      const content = buffer.toString("utf8").replace(/\r\n/g, "\n");
      const contentBytes = Buffer.byteLength(content, "utf8");
      totalBytes += contentBytes;

      if (totalBytes > options.maxBytes) {
        throw new ContextCollectionError(
          `Total context bytes (${totalBytes}) exceeds maxBytes limit of ${options.maxBytes}`
        );
      }

      const sha256 = createHash("sha256").update(content, "utf8").digest("hex");
      collected.push({
        path: relPath,
        content,
        sha256,
      });
    }

    return {
      commitSha,
      baseRef: options.baseRef,
      headRef: options.headRef,
      files: collected,
      diffs,
    };
  }
}
