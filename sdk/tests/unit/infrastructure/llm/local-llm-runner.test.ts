import { describe, expect, it } from "vitest";
import { LocalLlmRunner } from "../../../../src/infrastructure/llm/local-llm-runner.js";
import { LlmExecutionError } from "../../../../src/domain/llm-execution-error.js";
import { RepositoryContext } from "../../../../src/application/ports/git-context-collector.port.js";
import { Writable } from "node:stream";
import { AgentRunnerFactory } from "../../../../src/infrastructure/llm/agent-runner-factory.js";
import { existsSync } from "node:fs";
import { dirname } from "node:path";

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

  it("rejects an oversized Codex prompt before launching the executable", async () => {
    const missingRunner = new LocalLlmRunner(new AgentRunnerFactory([{
      type: "codex-cli", command: "non-existent-executable-987654321",
      buildArgs: () => [], parseOutput: (stdout) => stdout,
    }]));
    await expect(missingRunner.run({
      agent: "codex-cli", model: "test-model", effort: "high",
      timeoutSeconds: 5,
      projectKey: "catalog", environment: "staging",
      context: { ...dummyContext, files: [{ path: "large.ts", sha256: "abc", content: "x".repeat(1_048_576) }] },
    })).rejects.toThrow(/Codex input.*1048576.*--exclude-paths/);
  });

  it("fails with LlmExecutionError when executable is not found", async () => {
    await expect(
      runner.run({
        agent: "codex-cli",
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

  it("reports the resolved default executable when it is not found", async () => {
    const executable = "non-existent-default-executable-987654321";
    const missingRunner = new LocalLlmRunner(new AgentRunnerFactory([{
      type: "codex-cli",
      command: executable,
      buildArgs: () => [],
      parseOutput: (stdout) => stdout,
    }]));

    await expect(missingRunner.run({
      agent: "codex-cli",
      model: "test-model",
      effort: "high",
      timeoutSeconds: 5,
      projectKey: "catalog",
      environment: "staging",
      context: dummyContext,
    })).rejects.toThrow(`LLM executable not found: '${executable}'`);
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
      agent: "codex-cli",
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

  it("reads the graph from the prompted temporary JSON file when stdout has no graph", async () => {
    const script = `
      const fs = require('node:fs');
      let input = '';
      process.stdin.on('data', chunk => { input += chunk; });
      process.stdin.on('end', () => {
        const payload = JSON.parse(input);
        const match = payload.instruction.match(/<temporary_output_file>([\\s\\S]*?)<\\/temporary_output_file>/);
        if (!match) process.exit(13);
        const outputFile = JSON.parse(match[1]);
        if (!outputFile.endsWith('graph-output.json')) process.exit(14);
        const doc = {
          schema_version: '1.0',
          entities: [{ key: 'service:file-output', type: 'service' }],
          relations: [],
          evidence: [],
          metadata: { test_output_file: outputFile }
        };
        fs.writeFileSync(outputFile, JSON.stringify(doc));
      });
    `;

    const doc = await runner.run({
      agent: "codex-cli",
      model: "test-model",
      effort: "medium",
      llmCommand: process.execPath,
      timeoutSeconds: 10,
      projectKey: "catalog",
      environment: "staging",
      context: dummyContext,
      commandArgs: ["-e", script],
    });

    const outputFile = doc.metadata?.test_output_file as string;
    expect(outputFile).toMatch(/[\\/]graph-output\.json$/);
    expect(doc.entities[0].key).toBe("service:file-output");
    expect(existsSync(outputFile)).toBe(false);
    expect(existsSync(dirname(outputFile))).toBe(false);
  });

  it("fails with LlmExecutionError when process outputs invalid json", async () => {
    const script = `
      process.stdout.write("not valid json at all");
    `;

    await expect(
      runner.run({
        agent: "codex-cli",
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
        agent: "codex-cli",
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
      agent: "codex-cli",
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

  it("passes the complete context as the Copilot prompt argument", async () => {
    const script = `
      const payload = JSON.parse(process.argv[1]);
      const doc = {
        schema_version: '1.0',
        entities: [{ key: 'files:' + payload.context.files.length, type: 'service' }],
        relations: [],
        evidence: []
      };
      process.stdout.write(JSON.stringify(doc));
    `;
    const copilot = new LocalLlmRunner(new AgentRunnerFactory([{
      type: "copilot-cli",
      promptTransport: "argument",
      command: process.execPath,
      buildArgs: (_options, prompt) => ["-e", script, prompt ?? ""],
      parseOutput: (stdout) => stdout,
    }]));

    const doc = await copilot.run({
      agent: "copilot-cli",
      model: "gpt-5",
      effort: "high",
      timeoutSeconds: 10,
      projectKey: "catalog",
      environment: "staging",
      context: dummyContext,
    });

    expect(doc.entities[0].key).toBe("files:1");
  });
});

