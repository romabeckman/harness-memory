import { describe, expect, it } from "vitest";
import { SourceBatchPlanner } from "../../../../src/application/memory/source-batch-planner.js";

describe("SourceBatchPlanner", () => {
  it("preserves every character when one source file needs multiple batches", () => {
    const content = "😀\\\n".repeat(250_000);
    const batches = new SourceBatchPlanner().plan([{ path: "src/large.ts", content, sha256: "whole" }]);
    expect(batches.length).toBeGreaterThan(1);
    expect(batches.flat().map(part => part.content).join("")).toBe(content);
    expect(batches.every(batch => batch.reduce((size, file) => size + JSON.stringify(file).length + 1, 0) <= 350_000)).toBe(true);
  });
});
