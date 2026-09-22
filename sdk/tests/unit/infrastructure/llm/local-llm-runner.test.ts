import { describe, expect, it } from "vitest";
import { LocalLlmRunner } from "../../../../src/infrastructure/llm/local-llm-runner.js";
import { LlmExecutionError } from "../../../../src/domain/llm-execution-error.js";
import { RepositoryContext } from "../../../../src/application/ports/git-context-collector.port.js";
import { Writable } from "node:stream";

describe("LocalLlmRunner", () => {
  it("removes backpressure listeners after every drained write", async () => {
    const stdin = new Writable({ highWaterMark: 1, write(_chunk, _encoding, callback) { setImmediate(callback); } });
    const runner = new LocalLlmRunner();
    await (runner as any).streamPayloadToStdin(stdin, {
      projectKey: "demo", environment: "test", context: { commitSha: "a", headRef: "HEAD", diffs: [],
        files: Array.from({ length: 30 }, (_, i) => ({ path: `${i}.ts`, content: "content", sha256: "hash" })) },
    });
    expect(stdin.listenerCount("error")).toBe(0);
    expect(stdin.listenerCount("drain")).toBe(0);
  });
  const runner = new LocalLlmRunner();
  const dummyContext: RepositoryContext = {
    commitSha: "abc1234",
    headRef: "HEAD",
    files: [{ path: "index.ts", content: "export const x = 1;", sha256: "abc" }],
    diffs: [],
  };

  it("fails with LlmExecutionError when executable is not found", async () => {
    await expect(
      runner.run({
        model: "gpt-5",
        effort: "high",
        llmCommand: "non-existent-executable-987654321",
        timeoutSeconds: 5,
        projectKey: "catalog",
        environment: "staging",
        context: dummyContext,
      })
    ).rejects.toThrow(LlmExecutionError);
  });

  it("runs node script as fake llm and parses json stdout", async () => {
    // We can invoke node with an inline script that outputs valid JSON
    const script = `
      const fs = require('fs');
      process.stdin.resume();
      process.stdin.on('end', () => {
        const doc = {
          schema_version: '1.0',
          entities: [{ key: 'service:api', type: 'service' }],
          relations: [],
          evidence: []
        };
        process.stdout.write(JSON.stringify(doc));
      });
    `;

    const doc = await runner.run({
      model: "test-model",
      effort: "medium",
      llmCommand: process.execPath, // node
      timeoutSeconds: 10,
      projectKey: "catalog",
      environment: "staging",
      context: dummyContext,
      commandArgs: ["-e", script],
    });

    expect(doc.schema_version).toBe("1.0");
    expect(doc.entities).toHaveLength(1);
    expect(doc.entities[0].key).toBe("service:api");
  });

  it("fails with LlmExecutionError when process outputs invalid json", async () => {
    const script = `
      process.stdout.write("not valid json at all");
    `;

    await expect(
      runner.run({
        model: "test-model",
        effort: "low",
        llmCommand: process.execPath,
        timeoutSeconds: 5,
        projectKey: "catalog",
        environment: "staging",
        context: dummyContext,
        commandArgs: ["-e", script],
      })
    ).rejects.toThrow(LlmExecutionError);
  });

  it("fails with LlmExecutionError when process exits with non-zero code", async () => {
    const script = `
      process.stderr.write("fatal model failure");
      process.exit(1);
    `;

    await expect(
      runner.run({
        model: "test-model",
        effort: "low",
        llmCommand: process.execPath,
        timeoutSeconds: 5,
        projectKey: "catalog",
        environment: "staging",
        context: dummyContext,
        commandArgs: ["-e", script],
      })
    ).rejects.toThrow(LlmExecutionError);
  });

  it("streams repository context via stdin without monolithic payload allocation", async () => {
    const script = `
      let input = '';
      process.stdin.on('data', chunk => { input += chunk; });
      process.stdin.on('end', () => {
        const parsed = JSON.parse(input);
        const doc = {
          schema_version: '1.0',
          entities: [{ key: 'file-count:' + parsed.context.files.length, type: 'service' }],
          relations: [],
          evidence: []
        };
        process.stdout.write(JSON.stringify(doc));
      });
    `;

    const multiFileContext: RepositoryContext = {
      commitSha: "abc1234",
      headRef: "HEAD",
      files: [
        { path: "f1.ts", content: "const a = 1;", sha256: "h1" },
        { path: "f2.ts", content: "const b = 2;", sha256: "h2" },
        { path: "f3.ts", content: "const c = 3;", sha256: "h3" },
      ],
      diffs: [],
    };

    const doc = await runner.run({
      model: "test-model",
      effort: "medium",
      llmCommand: process.execPath,
      timeoutSeconds: 10,
      projectKey: "catalog",
      environment: "staging",
      context: multiFileContext,
      commandArgs: ["-e", script],
    });

    expect(doc.entities[0].key).toBe("file-count:3");
  });
});

