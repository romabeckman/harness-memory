import { GraphDocument, PublishSnapshotOptions } from "../../domain/contracts.js";
import { ConfigurationError } from "../../domain/configuration-error.js";
import { ContextCollectionError } from "../../domain/context-collection-error.js";
import { GraphValidationError } from "../../domain/graph-validation-error.js";
import { DocsStorePort } from "../ports/docs-store.port.js";
import { RepositoryContext } from "../ports/git-context-collector.port.js";
import { GraphValidatorPort } from "../ports/graph-validator.port.js";
import { LlmRunnerPort } from "../ports/llm-runner.port.js";
import { MemoryWorkflowPort } from "../ports/memory-workflow.port.js";
import { PublicationBaselinePort } from "../ports/publication-baseline.port.js";
import { DOCUMENT_TYPES, isMemoryPath, MemoryGraph } from "./memory-graph.js";
import { PROJECT_MEMORY_PROMPT } from "./project-memory-prompt.js";
import { DocumentContentCodec } from "./document-content-codec.js";

export class ProjectMemoryWorkflow implements MemoryWorkflowPort {
  constructor(private readonly llm: LlmRunnerPort, private readonly baseline: PublicationBaselinePort,
    private readonly docs: DocsStorePort, private readonly validator: GraphValidatorPort) {}

  async run(options: PublishSnapshotOptions, context: RepositoryContext): Promise<GraphDocument> {
    if (!options.dryRun && (!options.apiUrl || !options.token)) throw new ConfigurationError("apiUrl and token are required for publication");
    const stored = options.apiUrl && options.token
      ? await this.baseline.load(options.apiUrl, options.token, options.projectKey, options.environment) : undefined;
    const codec = new DocumentContentCodec();
    if (stored) this.validator.validateAndCanonicalize(stored);
    const previous = stored ? codec.decode(stored) : undefined;
    const files = this.docs.read(options.repository);
    const code = context.files.filter(f => !isMemoryPath(f.path) && !/^docs\/(workflow|harness-history)\//.test(f.path));
    const allFiles = [...code, ...files];
    if (allFiles.length > (options.maxFiles ?? 2000) || allFiles.reduce((size, f) => size + Buffer.byteLength(f.content), 0) > (options.maxBytes ?? 10485760)) {
      throw new ContextCollectionError("Code and documentation exceed the configured context budget");
    }
    const memory = new MemoryGraph();
    const seed = memory.seed(files, context.commitSha);
    this.validator.validateAndCanonicalize(codec.encode(seed));
    const proposed = await this.llm.run({ agent: options.agent, model: options.model, effort: options.effort,
      llmCommand: options.llmCommand, timeoutSeconds: options.timeout ?? 600,
      projectKey: options.projectKey, environment: options.environment,
      context: { ...context, files: [...code, ...files.filter(f => f.path === "docs/.graph.json")] }, instruction: PROJECT_MEMORY_PROMPT,
      baselineGraph: previous, documentationGraph: seed });
    const decoded = codec.decode(proposed);
    this.validator.validateAndCanonicalize(codec.encode(decoded));
    const graph = memory.reconcile(decoded, seed, previous);
    const paths = new Set<string>();
    for (const entity of graph.entities.filter(e => DOCUMENT_TYPES.has(e.type))) {
      const path = entity.metadata?.path;
      if (typeof path !== "string" || !isMemoryPath(path) || path === "docs/.graph.json") throw new GraphValidationError(`Invalid document path for '${entity.key}'`);
      if (paths.has(path)) throw new GraphValidationError(`Duplicate document path: ${path}`);
      if (typeof entity.metadata?.content !== "string" || !entity.metadata.content.trim()) throw new GraphValidationError(`Empty document: ${path}`);
      paths.add(path);
      entity.metadata.source_commit_sha = context.commitSha;
      const original = files.find(f => f.path === path);
      if (!original || original.content !== entity.metadata.content) {
        entity.metadata.generated_by = "harness-memory-sdk";
        entity.metadata.memory_protocol = "project-memory/v1";
      }
    }
    for (const path of ["docs/adr/ARCHITECTURE.md", "docs/adr/TESTS.md", "docs/.digest.md", "docs/README.md"]) {
      if (!paths.has(path)) throw new GraphValidationError(`Documentation bootstrap must produce ${path}`);
    }
    if (!graph.entities.some(e => e.type === "feature" && e.metadata?.lifecycle !== "removed")) throw new GraphValidationError("Documentation must describe at least one project feature");
    for (const rule of graph.entities.filter(e => e.type === "rule")) {
      if (typeof rule.metadata?.statement !== "string" || !rule.metadata.statement.trim()) throw new GraphValidationError(`Rule '${rule.key}' needs its complete statement`);
      const defines = graph.relations.find(r => r.type === "defines" && r.target_entity_key === rule.key);
      if (!defines || !graph.evidence.some(e => e.relation_ref === defines.ref)) throw new GraphValidationError(`Rule '${rule.key}' needs document scope and evidence`);
    }
    const validated = this.validator.validateAndCanonicalize(codec.encode(graph)).document;
    if (!options.dryRun) this.docs.write(options.repository, validated, files);
    return validated;
  }
}
