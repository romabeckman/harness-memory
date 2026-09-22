import { PublicationResult, PublishSnapshotOptions } from "../../domain/contracts.js";
import { ConfigurationError } from "../../domain/configuration-error.js";
import { GitContextCollectorPort } from "../ports/git-context-collector.port.js";
import { LlmRunnerPort } from "../ports/llm-runner.port.js";
import { GraphValidatorPort } from "../ports/graph-validator.port.js";
import { PublicationClientPort } from "../ports/publication-client.port.js";

export class PublishSnapshotUseCase {
  constructor(
    private readonly gitCollector: GitContextCollectorPort,
    private readonly llmRunner: LlmRunnerPort,
    private readonly graphValidator: GraphValidatorPort,
    private readonly publicationClient: PublicationClientPort
  ) {}

  public async execute(options: PublishSnapshotOptions): Promise<PublicationResult> {
    this.validateOptions(options);

    const context = await this.gitCollector.collect({
      repository: options.repository,
      baseRef: options.baseRef,
      headRef: options.headRef || "HEAD",
      maxFiles: options.maxFiles ?? 2000,
      maxBytes: options.maxBytes ?? 10485760,
    });

    const rawDocument = await this.llmRunner.run({
      model: options.model,
      effort: options.effort,
      llmCommand: options.llmCommand ?? "codex",
      timeoutSeconds: options.timeout ?? 600,
      projectKey: options.projectKey,
      environment: options.environment,
      context,
    });

    const validatedGraph = this.graphValidator.validateAndCanonicalize(rawDocument);

    if (options.dryRun) {
      return {
        status: "DRY_RUN",
        projectKey: options.projectKey,
        environment: options.environment,
        deploymentId: options.deploymentId,
        version: options.version,
        payloadSha256: validatedGraph.sha256,
        counts: validatedGraph.counts,
      };
    }

    const apiUrl = options.apiUrl;
    const token = options.token;
    if (!apiUrl || !token) {
      throw new ConfigurationError("apiUrl and token are required when dryRun is false");
    }

    return await this.publicationClient.publish({
      apiUrl,
      token,
      projectKey: options.projectKey,
      environment: options.environment,
      deploymentId: options.deploymentId,
      version: options.version,
      graph: validatedGraph,
    });
  }

  private validateOptions(options: PublishSnapshotOptions): void {
    if (!options.projectKey || !options.projectKey.trim()) {
      throw new ConfigurationError("projectKey is required");
    }
    if (!options.environment || !options.environment.trim()) {
      throw new ConfigurationError("environment is required");
    }
    if (!options.deploymentId || !options.deploymentId.trim()) {
      throw new ConfigurationError("deploymentId is required");
    }
    if (!options.version || !options.version.trim()) {
      throw new ConfigurationError("version is required");
    }
    if (!options.model || !options.model.trim()) {
      throw new ConfigurationError("model is required");
    }
    if (!options.effort || !["low", "medium", "high", "xhigh"].includes(options.effort)) {
      throw new ConfigurationError("effort must be one of: low, medium, high, xhigh");
    }
  }
}
