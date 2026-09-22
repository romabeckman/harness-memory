import { PublicationResult, PublishSnapshotOptions } from "../../domain/contracts.js";
import { ConfigurationError } from "../../domain/configuration-error.js";
import { GitContextCollectorPort } from "../ports/git-context-collector.port.js";
import { LlmRunnerPort } from "../ports/llm-runner.port.js";
import { GraphValidatorPort } from "../ports/graph-validator.port.js";
import { PublicationClientPort } from "../ports/publication-client.port.js";
import { DEFAULT_LLM_AGENT } from "../../domain/llm-agent.js";
import { MemoryWorkflowPort } from "../ports/memory-workflow.port.js";

export class PublishSnapshotUseCase {
  constructor(
    private readonly gitCollector: GitContextCollectorPort,
    private readonly llmRunner: LlmRunnerPort,
    private readonly graphValidator: GraphValidatorPort,
    private readonly publicationClient: PublicationClientPort,
    private readonly memoryWorkflow?: MemoryWorkflowPort
  ) {}

  public async execute(options: PublishSnapshotOptions): Promise<PublicationResult> {
    this.validateOptions(options);
    const token = options.token || process.env.HARNESS_MEMORY_API_KEY;
    const resolvedOptions = { ...options, token };

    const context = await this.gitCollector.collect({
      repository: options.repository,
      baseRef: options.baseRef,
      headRef: options.headRef || "HEAD",
      maxFiles: options.maxFiles ?? 2000,
      maxBytes: options.maxBytes ?? 10485760,
    });

    const rawDocument = this.memoryWorkflow ? await this.memoryWorkflow.run(resolvedOptions, context) : await this.llmRunner.run({
      agent: options.agent ?? DEFAULT_LLM_AGENT,
      model: options.model,
      effort: options.effort,
      llmCommand: options.llmCommand,
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
