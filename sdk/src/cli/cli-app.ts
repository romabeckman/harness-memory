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
    try {
      // Allow optional command name "publish": harness-memory publish [options]
      const args = rawArgs[0] === "publish" ? rawArgs.slice(1) : rawArgs;

      const config = this.configResolver.resolve(args, this.env);

      const useCase = new PublishSnapshotUseCase(
        new GitContextCollector(),
        new LocalLlmRunner(),
        new GraphValidator(),
        new RestPublicationClient(),
        new ProjectMemoryWorkflow(new LocalLlmRunner(), new PublicationBaselineClient(), new LocalDocsStore(), new GraphValidator())
      );

      if (config.verbose) {
        this.stderr(`[INFO] Analyzing repository at '${config.repository}'...`);
        this.stderr(`[INFO] Target environment: '${config.environment}', project: '${config.projectKey}'`);
      }

      const result = await useCase.execute(config);

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
      if (err instanceof PublisherError) {
        this.stderr(`Error [${err.name}]: ${err.message}`);
        return err.exitCode;
      }

      this.stderr(`Unexpected error: ${err?.message ?? String(err)}`);
      return ExitCode.USAGE_OR_CONFIG;
    }
  }
}
