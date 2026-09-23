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
import { SOURCE_SUMMARY_PROMPT } from "./project-memory-prompt.js";
import { SourceBatchPlanner } from "./source-batch-planner.js";
import { digest } from "./memory-graph.js";

export class ProjectMemoryWorkflow implements MemoryWorkflowPort {
  private readonly codec = new DocumentContentCodec();
  private readonly memory = new MemoryGraph();
  private readonly documentValidator = new MemoryDocumentValidator();
  private readonly batchPlanner = new SourceBatchPlanner();

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
    const existingDocs = this.hasCompleteProjectMemory(files);
    const code = this.collectCode(context, files, options, existingDocs);
    const seed = this.memory.seed(files, context.commitSha);
    this.validator.validateAndCanonicalize(this.codec.encode(seed));

    const proposed = await this.generate(options, context, code, files, previous, seed, existingDocs);
    const decoded = this.codec.decode(proposed);
    this.validator.validateAndCanonicalize(this.codec.encode(decoded));

    const graph = this.memory.reconcile(decoded, seed, previous, existingDocs);
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
    context: RepositoryContext, files: CollectedFile[], options: PublishSnapshotOptions, existingDocs: boolean,
  ): CollectedFile[] {
    const code = existingDocs ? [] : context.files.filter(file =>
      !isMemoryPath(file.path) && !/^docs\/(workflow|harness-history)\//.test(file.path));
    const allFiles = [...code, ...files];
    const bytes = allFiles.reduce((size, file) => size + Buffer.byteLength(file.content), 0);
    if (allFiles.length > (options.maxFiles ?? 2000) || bytes > (options.maxBytes ?? 10485760)) {
      throw new ContextCollectionError("Code and documentation exceed the configured context budget");
    }
    return code;
  }

  private hasCompleteProjectMemory(files: CollectedFile[]): boolean {
    const paths = new Set(files.map(file => file.path));
    const required = ["docs/.graph.json", "docs/.digest.md", "docs/README.md",
      "docs/adr/ARCHITECTURE.md", "docs/adr/TESTS.md"];
    if (!required.every(path => paths.has(path))) return false;
    const graphDocuments = files.filter(file => /^docs\/(adr|feature)\/.*\.md$/.test(file.path));
    if (!graphDocuments.some(file => file.path.startsWith("docs/feature/"))) return false;
    return graphDocuments.every(file => /^---\r?\n/.test(file.content) &&
      /^node_id:\s*["']?[\w-]+:[\w-]+["']?\s*$/m.test(file.content) &&
      (!file.path.startsWith("docs/feature/") || /```graph\s*\r?\n\s*\{/.test(file.content)));
  }

  private async generate(
    options: PublishSnapshotOptions,
    context: RepositoryContext,
    code: CollectedFile[],
    files: CollectedFile[],
    previous: GraphDocument | undefined,
    seed: GraphDocument,
    existingDocs: boolean,
  ): Promise<GraphDocument> {
    let promptFiles = existingDocs ? [] : [...code, ...files.filter(file => file.path === "docs/.graph.json")];
    let instruction = PROJECT_MEMORY_PROMPT;
    if (existingDocs) {
      instruction += "\nCurrent docs are authoritative: compare current documents with the latest published graph. Preserve local Markdown exactly; describe supported changes in graph facts and evidence. Do not invent source-file changes.";
    } else if (promptFiles.reduce((size, file) => size + JSON.stringify(file).length + 1, 0) > 500_000) {
      promptFiles = await this.summarizeSource(options, context, code);
      promptFiles.push(...files.filter(file => file.path === "docs/.graph.json"));
      instruction += "\nThe supplied source-manifest and source-summary files are intermediate context generated from all collected source files. Use only original paths from the manifest in evidence and document routing; never cite .harness-memory paths. Create complete project-memory documents from the summaries and local documentation.";
    }
    return this.llm.run({
      agent: options.agent,
      model: options.model,
      effort: options.effort,
      llmCommand: options.llmCommand,
      timeoutSeconds: options.timeout ?? 600,
      projectKey: options.projectKey,
      environment: options.environment,
      context: { ...context, files: promptFiles },
      instruction,
      baselineGraph: previous,
      documentationGraph: seed,
    });
  }

  private async summarizeSource(
    options: PublishSnapshotOptions, context: RepositoryContext, code: CollectedFile[],
  ): Promise<CollectedFile[]> {
    const summaries: CollectedFile[] = [];
    const batches = this.batchPlanner.plan(code);
    for (let index = 0; index < batches.length; index++) {
      const summary = await this.llm.run({
        agent: options.agent, model: options.model, effort: options.effort,
        llmCommand: options.llmCommand, timeoutSeconds: options.timeout ?? 600,
        projectKey: options.projectKey, environment: options.environment,
        context: { ...context, files: batches[index], diffs: [] },
        instruction: SOURCE_SUMMARY_PROMPT,
      });
      this.validator.validateAndCanonicalize(summary);
      const content = JSON.stringify(summary);
      if (content.length > 80_000) throw new ContextCollectionError(`Source summary ${index + 1} exceeds 80000 characters`);
      summaries.push({ path: `.harness-memory/source-summary-${index + 1}.json`, content, sha256: digest(content) });
    }
    const manifest = JSON.stringify(code.map(file => ({ path: file.path, sha256: file.sha256 })));
    return [{ path: ".harness-memory/source-manifest.json", content: manifest, sha256: digest(manifest) }, ...summaries];
  }
}
