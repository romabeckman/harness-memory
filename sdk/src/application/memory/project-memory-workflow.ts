import type { GraphDocument, PublishSnapshotOptions } from "../../domain/contracts.js";
import { ConfigurationError } from "../../domain/configuration-error.js";
import { ContextCollectionError } from "../../domain/context-collection-error.js";
import type { DocsStorePort } from "../ports/docs-store.port.js";
import type { CollectedFile, RepositoryContext } from "../ports/git-context-collector.port.js";
import type { GraphValidatorPort } from "../ports/graph-validator.port.js";
import type { LlmRunnerPort } from "../ports/llm-runner.port.js";
import type { MemoryWorkflowPort } from "../ports/memory-workflow.port.js";
import type { PublicationBaselinePort } from "../ports/publication-baseline.port.js";
import { DocumentContentCodec } from "./document-content-codec.js";
import { MemoryDocumentValidator } from "./memory-document-validator.js";
import { isMemoryPath, MemoryGraph } from "./memory-graph.js";
import { PROJECT_MEMORY_PROMPT } from "./project-memory-prompt.js";

export class ProjectMemoryWorkflow implements MemoryWorkflowPort {
  private readonly codec = new DocumentContentCodec();
  private readonly memory = new MemoryGraph();
  private readonly documentValidator = new MemoryDocumentValidator();

  constructor(
    private readonly llm: LlmRunnerPort,
    private readonly baseline: PublicationBaselinePort,
    private readonly docs: DocsStorePort,
    private readonly validator: GraphValidatorPort,
  ) {}

  public async run(options: PublishSnapshotOptions, context: RepositoryContext): Promise<GraphDocument> {
    this.validatePublicationOptions(options);
    const previous = await this.loadPrevious(options);
    const files = this.docs.read(options.repository);
    const code = this.collectCode(context, files, options);
    const seed = this.memory.seed(files, context.commitSha);
    this.validator.validateAndCanonicalize(this.codec.encode(seed));

    const proposed = await this.generate(options, context, code, files, previous, seed);
    const decoded = this.codec.decode(proposed);
    this.validator.validateAndCanonicalize(this.codec.encode(decoded));

    const graph = this.memory.reconcile(decoded, seed, previous);
    this.documentValidator.validateAndEnrich(graph, files, context.commitSha);
    const validated = this.validator.validateAndCanonicalize(this.codec.encode(graph)).document;
    if (!options.dryRun) this.docs.write(options.repository, validated, files);
    return validated;
  }

  private validatePublicationOptions(options: PublishSnapshotOptions): void {
    if (!options.dryRun && (!options.apiUrl || !options.token)) {
      throw new ConfigurationError("apiUrl and token are required for publication");
    }
  }

  private async loadPrevious(options: PublishSnapshotOptions): Promise<GraphDocument | undefined> {
    if (!options.apiUrl || !options.token) return undefined;
    const stored = await this.baseline.load(
      options.apiUrl, options.token, options.projectKey, options.environment,
    );
    if (!stored) return undefined;
    this.validator.validateAndCanonicalize(stored);
    return this.codec.decode(stored);
  }

  private collectCode(
    context: RepositoryContext, files: CollectedFile[], options: PublishSnapshotOptions,
  ): CollectedFile[] {
    const code = context.files.filter(file =>
      !isMemoryPath(file.path) && !/^docs\/(workflow|harness-history)\//.test(file.path));
    const allFiles = [...code, ...files];
    const bytes = allFiles.reduce((size, file) => size + Buffer.byteLength(file.content), 0);
    if (allFiles.length > (options.maxFiles ?? 2000) || bytes > (options.maxBytes ?? 10485760)) {
      throw new ContextCollectionError("Code and documentation exceed the configured context budget");
    }
    return code;
  }

  private async generate(
    options: PublishSnapshotOptions,
    context: RepositoryContext,
    code: CollectedFile[],
    files: CollectedFile[],
    previous: GraphDocument | undefined,
    seed: GraphDocument,
  ): Promise<GraphDocument> {
    return this.llm.run({
      agent: options.agent,
      model: options.model,
      effort: options.effort,
      llmCommand: options.llmCommand,
      timeoutSeconds: options.timeout ?? 600,
      projectKey: options.projectKey,
      environment: options.environment,
      context: { ...context, files: [...code, ...files.filter(file => file.path === "docs/.graph.json")] },
      instruction: PROJECT_MEMORY_PROMPT,
      baselineGraph: previous,
      documentationGraph: seed,
    });
  }
}
