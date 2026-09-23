import { ConfigResolver } from "../infrastructure/config/config-resolver.js";
import { GitContextCollector } from "../infrastructure/git/git-context-collector.js";
import { LocalLlmRunner } from "../infrastructure/llm/local-llm-runner.js";
import { GraphValidator } from "../infrastructure/validator/graph-validator.js";
import { RestPublicationClient } from "../infrastructure/api/rest-publication-client.js";
import { PublishSnapshotUseCase } from "../application/publish-snapshot/publish-snapshot.use-case.js";
import { ExitCode } from "../domain/exit-code.js";
import { PublisherError } from "../domain/publisher-error.js";
import { ProjectMemoryWorkflow } from "../application/memory/project-memory-workflow.js";
import { PublicationBaselineClient } from "../infrastructure/api/publication-baseline-client.js";
import { LocalDocsStore } from "../infrastructure/memory/local-docs-store.js";
import type { PublicationProgressEvent } from "../application/publish-snapshot/phases/publication-phase-context.js";

export interface CliIo {
  stdout?: (msg: string) => void;
  stderr?: (msg: string) => void;
  env?: Record<string, string | undefined>;
}

export class CliApp {
  private readonly stdout: (msg: string) => void;
  private readonly stderr: (msg: string) => void;
  private readonly env: Record<string, string | undefined>;
  private readonly configResolver: ConfigResolver;

  constructor(io?: CliIo) {
    this.stdout = io?.stdout ?? ((msg: string) => process.stdout.write(msg + "\n"));
    this.stderr = io?.stderr ?? ((msg: string) => process.stderr.write(msg + "\n"));
    this.env = io?.env ?? process.env;
    this.configResolver = new ConfigResolver();
  }

  public async run(rawArgs: string[]): Promise<ExitCode> {
    let debugEnabled = rawArgs.includes("--debug") || this.env.HARNESS_MEMORY_DEBUG === "true";
    let token: string | undefined;
    try {
      // Allow optional command name "publish": harness-memory publish [options]
      const args = rawArgs[0] === "publish" ? rawArgs.slice(1) : rawArgs;

      const config = this.configResolver.resolve(args, this.env);
      debugEnabled = config.debug;
      token = config.token;
      const debug = config.debug
        ? (message: string) => this.stderr(`[debug] ${this.redact(message, token)}`)
        : undefined;

      debug?.(`Configuration: ${JSON.stringify({ agent: config.agent, model: config.model,
        effort: config.effort, projectKey: config.projectKey, environment: config.environment,
        dryRun: config.dryRun })}`);

      const useCase = new PublishSnapshotUseCase(
        new GitContextCollector(),
        new LocalLlmRunner(),
        new GraphValidator(),
        new RestPublicationClient(),
        new ProjectMemoryWorkflow(new LocalLlmRunner(), new PublicationBaselineClient(), new LocalDocsStore(), new GraphValidator(), debug)
      );

      if (config.verbose) {
        this.stderr(`Repository: ${config.repository}`);
        this.stderr(`Target: ${config.projectKey} (${config.environment})`);
      }

      const phaseStartedAt = new Map<string, number>();
      const result = await useCase.execute(config, (event) => {
        this.reportProgress(event);
        if (!debug) return;
        if (event.state === "started") {
          phaseStartedAt.set(event.phase, Date.now());
          debug(`Phase ${event.phase} started`);
        } else {
          const duration = Date.now() - (phaseStartedAt.get(event.phase) ?? Date.now());
          debug(`Phase ${event.phase} ${event.state} in ${duration} ms`);
        }
      });
      debug?.(`Result: status=${result.status}, entities=${result.counts?.entities ?? 0}, ` +
        `relations=${result.counts?.relations ?? 0}, evidence=${result.counts?.evidence ?? 0}`);

      if (config.outputFormat === "json") {
        const jsonOutput = JSON.stringify(
          {
            status: result.status,
            publication_id: result.publicationId ?? null,
            snapshot_id: result.snapshotId ?? null,
            project_key: result.projectKey,
            environment: result.environment,
            deployment_id: result.deploymentId,
            version: result.version,
            payload_sha256: result.payloadSha256,
            counts: result.counts ?? { entities: 0, relations: 0, evidence: 0 },
          },
          null,
          2
        );
        this.stdout(jsonOutput);
      } else {
        this.stdout(
          `Publication Result:\n` +
            `  Status:         ${result.status}\n` +
            `  Project:        ${result.projectKey}\n` +
            `  Environment:    ${result.environment}\n` +
            `  Deployment ID:  ${result.deploymentId}\n` +
            `  Version:        ${result.version}\n` +
            `  Payload SHA256: ${result.payloadSha256}\n` +
            `  Counts:         entities=${result.counts?.entities ?? 0}, relations=${result.counts?.relations ?? 0}, evidence=${result.counts?.evidence ?? 0}`
        );
      }

      return ExitCode.SUCCESS;
    } catch (err: any) {
      if (debugEnabled) {
        const stack = err instanceof Error ? err.stack ?? `${err.name}: ${err.message}` : String(err);
        this.stderr(`[debug] Error stack:\n${this.redact(stack, token)}`);
      }
      if (err instanceof PublisherError) {
        this.stderr(`Error [${err.name}]: ${this.redact(err.message, token)}`);
        return err.exitCode;
      }

      this.stderr(`Unexpected error: ${this.redact(err?.message ?? String(err), token)}`);
      return ExitCode.USAGE_OR_CONFIG;
    }
  }

  private reportProgress(event: PublicationProgressEvent): void {
    if (event.state === "started") {
      this.stderr(`→ ${event.phase}...`);
      return;
    }

    if (event.state === "completed") {
      this.stderr(`✓ ${event.phase}`);
      return;
    }

    this.stderr(`✗ ${event.phase}`);
  }

  private redact(message: string, token?: string): string {
    let safe = message
      .replace(/([a-z][a-z0-9+.-]*:\/\/)[^/\s@]+@/gi, "$1[REDACTED]@")
      .replace(/(bearer\s+)\S+/gi, "$1[REDACTED]")
      .replace(/((?:token|secret|password|api[_-]?key)\s*[=:]\s*)\S+/gi, "$1[REDACTED]");
    const secrets = new Set([
      token,
      ...Object.entries(this.env)
        .filter(([name, value]) => /TOKEN|SECRET|PASSWORD|KEY|AUTH/i.test(name) && value)
        .map(([, value]) => value),
    ]);
    for (const secret of secrets) {
      if (secret) safe = safe.replaceAll(secret, "[REDACTED]");
    }
    return safe;
  }
}
