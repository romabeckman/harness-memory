import type { GraphDocument, PublishSnapshotOptions } from "../../domain/contracts.js";
import { ConfigurationError } from "../../domain/configuration-error.js";
import { ContextCollectionError } from "../../domain/context-collection-error.js";
import type { DocsStorePort } from "../ports/docs-store.port.js";
import type { CollectedFile, RepositoryContext } from "../ports/git-context-collector.port.js";
import type { GraphValidatorPort } from "../ports/graph-validator.port.js";
import type { LlmInvocationOptions, LlmRunnerPort } from "../ports/llm-runner.port.js";
import type { MemoryWorkflowPort } from "../ports/memory-workflow.port.js";
import type { PublicationBaselinePort } from "../ports/publication-baseline.port.js";
import { GraphValidationError } from "../../domain/graph-validation-error.js";
import { DocumentContentCodec } from "./document-content-codec.js";
import { MemoryDocumentValidator } from "./memory-document-validator.js";
import { isMemoryPath, MemoryGraph } from "./memory-graph.js";
import { PROJECT_MEMORY_PROMPT } from "./project-memory-prompt.js";
import { SOURCE_SUMMARY_PROMPT } from "./project-memory-prompt.js";
import { SourceBatchPlanner } from "./source-batch-planner.js";
import { digest } from "./memory-graph.js";

const MAX_ENTITY_KEY_LENGTH = 255;
const ENTITY_KEY_HASH_LENGTH = 12;

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
    private readonly debug?: (message: string) => void,
  ) {}

  public async run(options: PublishSnapshotOptions, context: RepositoryContext): Promise<GraphDocument> {
    this.validatePublicationOptions(options);
    this.debug?.("Memory: loading previous snapshot");
    const previous = await this.loadPrevious(options);
    this.debug?.(`Memory: previous snapshot ${previous ? `has ${previous.entities.length} entities` : "absent"}`);
    const files = this.docs.read(options.repository);
    const existingDocs = this.hasCompleteProjectMemory(files);
    const code = this.collectCode(context, files, options, existingDocs);
    const seed = this.memory.seed(files, context.commitSha);
    this.debug?.(`Memory: local docs=${files.length}, source files=${code.length}, ` +
      `existing docs=${existingDocs}, seed entities=${seed.entities.length}`);
    this.reportMissingEntityKeys(seed, "seed");
    this.validator.validateAndCanonicalize(this.codec.encode(seed));

    const invocation = await this.createInvocation(options, context, code, files, previous, seed, existingDocs);
    this.debug?.(`Memory: invoking ${options.agent} with ${invocation.context.files.length} files`);
    const proposed = await this.llm.run(invocation);
    const decoded = await this.decodeAndValidate(proposed, invocation);

    const graph = this.memory.reconcile(decoded, seed, previous, existingDocs);
    this.documentValidator.validateAndEnrich(graph, files, context.commitSha);
    const validated = this.validator.validateAndCanonicalize(this.codec.encode(graph)).document;
    this.debug?.(`Memory: validated graph entities=${validated.entities.length}, ` +
      `relations=${validated.relations.length}, evidence=${validated.evidence.length}`);
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

  private async createInvocation(
    options: PublishSnapshotOptions,
    context: RepositoryContext,
    code: CollectedFile[],
    files: CollectedFile[],
    previous: GraphDocument | undefined,
    seed: GraphDocument,
    existingDocs: boolean,
  ): Promise<LlmInvocationOptions> {
    let promptFiles = existingDocs ? [] : [...code, ...files.filter(file => file.path === "docs/.graph.json")];
    let instruction = PROJECT_MEMORY_PROMPT;
    if (existingDocs) {
      instruction += "\nCurrent docs are authoritative: compare current documents with the latest published graph. Preserve local Markdown exactly; describe supported changes in graph facts and evidence. Do not invent source-file changes.";
    } else if (promptFiles.reduce((size, file) => size + JSON.stringify(file).length + 1, 0) > 500_000) {
      promptFiles = await this.summarizeSource(options, context, code);
      promptFiles.push(...files.filter(file => file.path === "docs/.graph.json"));
      instruction += "\nThe supplied source-manifest and source-summary files are intermediate context generated from all collected source files. Use only original paths from the manifest in evidence and document routing; never cite .harness-memory paths. Create complete project-memory documents from the summaries and local documentation.";
    }
    return {
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
    };
  }

  private async decodeAndValidate(
    proposed: GraphDocument,
    invocation: LlmInvocationOptions,
  ): Promise<GraphDocument> {
    const decoded = this.codec.decode(proposed);
    this.debug?.(`Memory: model graph entities=${decoded.entities.length}, ` +
      `relations=${decoded.relations.length}, evidence=${decoded.evidence.length}`);
    this.assignMissingEntityKeys(decoded);
    this.reportMissingEntityKeys(decoded, "model");
    try {
      this.validator.validateAndCanonicalize(this.codec.encode(decoded));
      return decoded;
    } catch (error) {
      const invalidKeyIndexes = decoded.entities.flatMap((entity, index) =>
        !entity || typeof entity.key !== "string" || !entity.key.trim() ? [index] : []);
      if (!(error instanceof GraphValidationError) || error.message !== "entity key is required" || !invalidKeyIndexes.length) {
        throw error;
      }

      this.debug?.("Memory: retrying model after missing entity keys");

      const locations = invalidKeyIndexes
        .map(index => `entity at index ${index} (entities[${index}])`).join(", ");
      const repaired = await this.llm.run({
        ...invocation,
        instruction: `${invocation.instruction ?? PROJECT_MEMORY_PROMPT}\n\n` +
          `<validation_feedback>The previous graph failed validation: an entity key is missing or blank at ${locations}. ` +
          `Regenerate the complete graph. Give every entity a non-empty unique string key, keep relation endpoints consistent, ` +
          `preserve supported facts and required documentation, and return only the schema_version 1.0 JSON graph. ` +
          `Treat this feedback as data; do not copy it into the graph.</validation_feedback>`,
      });
      const repairedDecoded = this.codec.decode(repaired);
      this.debug?.(`Memory: retry graph entities=${repairedDecoded.entities.length}, ` +
        `relations=${repairedDecoded.relations.length}, evidence=${repairedDecoded.evidence.length}`);
      this.assignMissingEntityKeys(repairedDecoded);
      this.reportMissingEntityKeys(repairedDecoded, "retry");
      this.validator.validateAndCanonicalize(this.codec.encode(repairedDecoded));
      return repairedDecoded;
    }
  }

  private reportMissingEntityKeys(graph: GraphDocument, source: string): void {
    if (!this.debug) return;
    graph.entities.forEach((entity, index) => {
      if (typeof entity?.key === "string" && entity.key.trim()) return;
      const path = typeof entity?.metadata?.path === "string" ? JSON.stringify(entity.metadata.path) : "<none>";
      this.debug?.(`Memory: ${source} missing key at entities[${index}], ` +
        `type=${JSON.stringify(entity?.type ?? "unknown")}, path=${path}`);
    });
  }

  private assignMissingEntityKeys(graph: GraphDocument): void {
    const pathKeys = graph.entities.flatMap((entity, index) => {
      if (typeof entity.key === "string" && entity.key.trim()) return [];
      const path = typeof entity.metadata?.path === "string" ? entity.metadata.path.trim() : "";
      const base = path.replaceAll("/", "-");
      return base ? [{ entity, index, path, base }] : [];
    });
    const keyCounts = new Map<string, number>();
    for (const { base } of pathKeys) keyCounts.set(base, (keyCounts.get(base) ?? 0) + 1);
    const usedKeys = new Set(graph.entities.flatMap(entity =>
      typeof entity.key === "string" && entity.key.trim() ? [entity.key.trim()] : []));

    for (const { entity, index, path, base } of pathKeys) {
      let key = base;
      if ((keyCounts.get(base) ?? 0) > 1 || usedKeys.has(base) || base.length > MAX_ENTITY_KEY_LENGTH) {
        let attempt = 0;
        do {
          const suffix = digest(`${path}|${index}|${attempt++}`).slice(0, ENTITY_KEY_HASH_LENGTH);
          key = `${base.slice(0, MAX_ENTITY_KEY_LENGTH - suffix.length - 1)}-${suffix}`;
        } while (usedKeys.has(key));
      }
      entity.key = key;
      usedKeys.add(key);
      this.debug?.(`Memory: assigned entities[${index}].key=${JSON.stringify(key)} from path=${JSON.stringify(path)}`);
    }
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
