import { existsSync } from "node:fs";
import { spawn } from "node:child_process";
import { GraphDocument } from "../../domain/contracts.js";
import { LlmExecutionError } from "../../domain/llm-execution-error.js";
import {
  LlmInvocationOptions,
  LlmRunnerPort,
} from "../../application/ports/llm-runner.port.js";
import { AgentRunnerFactory } from "./agent-runner-factory.js";

const MAX_STDOUT_BYTES = 50 * 1024 * 1024;
const MAX_STDERR_BYTES = 1 * 1024 * 1024;
const MAX_CODEX_INPUT_CHARS = 1_048_576;

export interface ExtendedLlmInvocationOptions extends LlmInvocationOptions {
  commandArgs?: string[];
}

export class LocalLlmRunner implements LlmRunnerPort {
  constructor(private readonly agentRunnerFactory = new AgentRunnerFactory()) {}

  public async run(options: ExtendedLlmInvocationOptions): Promise<GraphDocument> {
    const agentRunner = this.agentRunnerFactory.create(options.agent);
    if (options.agent === "codex-cli" &&
      (!options.llmCommand?.trim() || /(?:^|[\\/\s])codex(?:\.cmd|\.exe)?(?:\s|$)/i.test(options.llmCommand))) {
      let inputChars = 0;
      for (const chunk of this.payloadChunks(options)) inputChars += chunk.length;
      if (inputChars > MAX_CODEX_INPUT_CHARS) {
        throw new LlmExecutionError(
          `Codex input has ${inputChars} characters, exceeding the ${MAX_CODEX_INPUT_CHARS} character limit. ` +
          "Use --exclude-paths with explicit source paths to reduce the context."
        );
      }
    }
    let execPath = options.llmCommand?.trim() || agentRunner.command;
    let baseArgs: string[] = [];

    if (!existsSync(execPath)) {
      const match = execPath.match(/^"([^"]+)"\s*(.*)$/);
      if (match) {
        execPath = match[1];
        baseArgs = match[2] ? match[2].trim().split(/\s+/) : [];
      } else {
        const parts = execPath.split(/\s+/);
        execPath = parts[0];
        baseArgs = parts.slice(1);
      }
    }

    const args = options.commandArgs ?? [...baseArgs, ...agentRunner.buildArgs(options)];

    // Minimal sanitized environment strictly excluding tokens and secrets
    const safeEnv: Record<string, string> = {};
    for (const [key, value] of Object.entries(process.env)) {
      if (!value) continue;
      const upper = key.toUpperCase();
      if (
        upper.includes("TOKEN") ||
        upper.includes("SECRET") ||
        upper.includes("PASSWORD") ||
        upper.includes("KEY") ||
        upper.includes("AUTH")
      ) {
        continue;
      }
      safeEnv[key] = value;
    }

    return new Promise<GraphDocument>((resolve, reject) => {
      let child: any;
      try {
        child = spawn(execPath, args, {
          shell: false,
          stdio: ["pipe", "pipe", "pipe"],
          env: safeEnv,
        });
        child.stdin.on("error", () => {
          // Ignore EPIPE/EOF errors if child terminates before reading stdin
        });
      } catch (err: any) {
        return reject(
          new LlmExecutionError(
            `Failed to spawn LLM command '${execPath}': ${err.message}`
          )
        );
      }

      let stdout = "";
      let stderr = "";
      let stdoutBytes = 0;
      let stderrBytes = 0;
      let killedDueToTimeout = false;

      const timeoutMs = (options.timeoutSeconds ?? 600) * 1000;
      const timer = setTimeout(() => {
        killedDueToTimeout = true;
        child.kill("SIGKILL");
      }, timeoutMs);

      child.on("error", (err: any) => {
        clearTimeout(timer);
        if (err.code === "ENOENT") {
          reject(
            new LlmExecutionError(
              `LLM executable not found: '${execPath}'`
            )
          );
        } else {
          reject(
            new LlmExecutionError(
              `LLM process error: ${this.redact(err.message)}`
            )
          );
        }
      });

      child.stdout.on("data", (chunk: Buffer) => {
        stdoutBytes += chunk.length;
        if (stdoutBytes > MAX_STDOUT_BYTES) {
          clearTimeout(timer);
          child.kill("SIGKILL");
          reject(
            new LlmExecutionError(
              `LLM stdout exceeded maximum limit of ${MAX_STDOUT_BYTES} bytes`
            )
          );
          return;
        }
        stdout += chunk.toString("utf8");
      });

      child.stderr.on("data", (chunk: Buffer) => {
        stderrBytes += chunk.length;
        if (stderrBytes <= MAX_STDERR_BYTES) {
          stderr += chunk.toString("utf8");
        }
      });

      child.on("close", (code: number | null, signal: string | null) => {
        clearTimeout(timer);

        if (killedDueToTimeout) {
          return reject(
            new LlmExecutionError(
              `LLM process timed out after ${options.timeoutSeconds} seconds`
            )
          );
        }

        if (code !== 0) {
          const redactedStderr = this.redact(stderr.trim());
          const reason = signal
            ? `terminated with signal ${signal}`
            : `exited with code ${code}`;
          return reject(
            new LlmExecutionError(
              `LLM process ${reason}${redactedStderr ? `: ${redactedStderr}` : ""}`
            )
          );
        }

        let trimmed: string;
        try {
          trimmed = agentRunner.parseOutput(stdout).trim();
        } catch (err: any) {
          return reject(
            err instanceof LlmExecutionError
              ? err
              : new LlmExecutionError(`Failed to read ${agentRunner.type} output`)
          );
        }
        if (!trimmed) {
          return reject(new LlmExecutionError("LLM process emitted empty stdout"));
        }

        let parsed: unknown;
        try {
          parsed = JSON.parse(trimmed);
        } catch (err: any) {
          return reject(
            new LlmExecutionError(
              `LLM output is not valid JSON: ${this.redact(err.message)}`
            )
          );
        }

        resolve(parsed as GraphDocument);
      });

      // Stream payload chunks iteratively respecting backpressure
      this.streamPayloadToStdin(child.stdin, options).catch((err: any) => {
        if (!child.killed) {
          clearTimeout(timer);
          child.kill("SIGKILL");
          reject(
            new LlmExecutionError(
              `Failed to write to LLM stdin: ${this.redact(err.message)}`
            )
          );
        }
      });
    });
  }

  private async streamPayloadToStdin(
    stdin: NodeJS.WritableStream,
    options: ExtendedLlmInvocationOptions
  ): Promise<void> {
    const writeChunk = (chunk: string): Promise<void> => {
      return new Promise((resolve, reject) => {
        if (!stdin.writable) {
          resolve();
          return;
        }
        const canContinue = stdin.write(chunk, "utf8");
        if (canContinue) {
          resolve();
        } else {
          const cleanup = () => {
            stdin.removeListener("drain", drained);
            stdin.removeListener("error", failed);
            stdin.removeListener("close", closed);
          };
          const drained = () => { cleanup(); resolve(); };
          const failed = (error: Error) => { cleanup(); reject(error); };
          const closed = () => { cleanup(); resolve(); };
          stdin.once("drain", drained);
          stdin.once("error", failed);
          stdin.once("close", closed);
        }
      });
    };

    for (const chunk of this.payloadChunks(options)) await writeChunk(chunk);
    stdin.end();
  }

  private *payloadChunks(options: ExtendedLlmInvocationOptions): Generator<string> {
    const envelope = {
      instruction: options.instruction ??
        "Generate a complete environment knowledge graph for the given repository and project. Output strictly one JSON document matching schema_version 1.0.",
      project_key: options.projectKey,
      environment: options.environment,
      baseline_graph: options.baselineGraph,
      documentation_graph: options.documentationGraph,
      context: {
        commit_sha: options.context.commitSha,
        base_ref: options.context.baseRef,
        head_ref: options.context.headRef,
        diffs: options.context.diffs,
      },
    };

    const envelopeStr = JSON.stringify(envelope);
    const prefix = (envelopeStr.endsWith("}}") ? envelopeStr.slice(0, -2) : envelopeStr.slice(0, -1)) + ',"files":[';
    yield prefix;

    const files = options.context.files;
    for (let i = 0; i < files.length; i++) {
      const f = files[i];
      const fileJson = JSON.stringify({
        path: f.path,
        sha256: f.sha256,
        content: f.content,
      });
      const separator = i === files.length - 1 ? "" : ",";
      yield fileJson + separator;
    }

    yield "]}}";
  }

  private redact(message: string): string {
    return message
      .replace(/(bearer\s+)[A-Za-z0-9_\-\.]+/gi, "$1[REDACTED]")
      .replace(/(token|secret|password)[=:\s]+[A-Za-z0-9_\-\.]+/gi, "$1=[REDACTED]");
  }
}
