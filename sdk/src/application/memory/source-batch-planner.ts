import type { CollectedFile } from "../ports/git-context-collector.port.js";
import { digest } from "./memory-graph.js";

const MAX_BATCH_CHARS = 350_000;

export class SourceBatchPlanner {
  public plan(files: CollectedFile[]): CollectedFile[][] {
    const batches: CollectedFile[][] = [];
    let batch: CollectedFile[] = [];
    let size = 0;
    for (const file of files) {
      for (const part of this.split(file)) {
        const length = JSON.stringify(part).length + 1;
        if (batch.length > 0 && size + length > MAX_BATCH_CHARS) {
          batches.push(batch);
          batch = [];
          size = 0;
        }
        batch.push(part);
        size += length;
      }
    }
    if (batch.length) batches.push(batch);
    return batches;
  }

  private split(file: CollectedFile): CollectedFile[] {
    if (JSON.stringify(file).length + 1 <= MAX_BATCH_CHARS) return [file];
    const middle = Math.floor(file.content.length / 2);
    const boundary = /[\uD800-\uDBFF]/.test(file.content[middle - 1] ?? "") ? middle - 1 : middle;
    const first = file.content.slice(0, boundary);
    const second = file.content.slice(boundary);
    if (!first || !second) throw new Error(`Cannot split source file '${file.path}' into prompt batches`);
    return [
      ...this.split({ path: file.path, content: first, sha256: digest(first) }),
      ...this.split({ path: file.path, content: second, sha256: digest(second) }),
    ];
  }
}
