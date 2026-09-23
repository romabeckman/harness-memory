import { beforeEach, describe, expect, it, vi } from "vitest";
import { PublishSnapshotUseCase } from "../../../src/application/publish-snapshot/publish-snapshot.use-case.js";
import { ConfigurationError } from "../../../src/domain/configuration-error.js";
import { GitContextCollectorPort } from "../../../src/application/ports/git-context-collector.port.js";
import { LlmRunnerPort } from "../../../src/application/ports/llm-runner.port.js";
import { GraphValidatorPort } from "../../../src/application/ports/graph-validator.port.js";
import { PublicationClientPort } from "../../../src/application/ports/publication-client.port.js";
import type { PublishSnapshotOptions } from "../../../src/domain/contracts.js";
import type { RepositoryContext } from "../../../src/application/ports/git-context-collector.port.js";

describe("PublishSnapshotUseCase", () => {
  beforeEach(() => vi.clearAllMocks());
  const mockCollector: GitContextCollectorPort = {
    collect: vi.fn().mockResolvedValue({
      commitSha: "commit-123",
      headRef: "HEAD",
      files: [],
      diffs: [],
    }),
  };

  const mockLlm: LlmRunnerPort = {
    run: vi.fn().mockResolvedValue({
      schema_version: "1.0",
      entities: [],
      relations: [],
      evidence: [],
    }),
  };

  const mockValidator: GraphValidatorPort = {
    validateAndCanonicalize: vi.fn().mockReturnValue({
      document: { schema_version: "1.0", entities: [], relations: [], evidence: [] },
      canonicalJson: "{}",
      sha256: "hash-abc",
      counts: { entities: 0, relations: 0, evidence: 0 },
    }),
  };

  const mockClient: PublicationClientPort = {
    validateTarget: vi.fn().mockResolvedValue("b0377492-0f1c-4a7e-ab65-e30c2424fd57"),
    publish: vi.fn().mockResolvedValue({
      status: "ACTIVATED",
      publicationId: "pub-1",
      snapshotId: "snap-1",
      projectKey: "catalog",
      environment: "staging",
      deploymentId: "dep-1",
      version: "1.0.0",
      payloadSha256: "hash-abc",
      counts: { entities: 0, relations: 0, evidence: 0 },
    }),
  };
  const memoryWorkflow = { run: vi.fn(async (options: PublishSnapshotOptions, context: RepositoryContext) => ({
    status: "READY" as const,
    graph: await mockLlm.run({ agent: options.agent, model: options.model, effort: options.effort,
      timeoutSeconds: 600, projectKey: options.projectKey, environment: options.environment, context }),
  })) };
  const documentationDirectory = { exists: vi.fn().mockReturnValue(true) };

  it("throws ConfigurationError when required fields are missing", async () => {
    const useCase = new PublishSnapshotUseCase(
      mockCollector,
      mockValidator,
      mockClient,
      memoryWorkflow,
      documentationDirectory
    );

    await expect(
      useCase.execute({
        agent: "codex-cli",
        repository: "",
        projectKey: "",
        environment: "staging",
        deploymentId: "dep-1",
        version: "1.0",
        model: "gpt-5",
        effort: "high",
        headRef: "HEAD",
        dryRun: true,
      })
    ).rejects.toThrow(ConfigurationError);
  });

  it("returns DRY_RUN without calling publication client when dryRun is true", async () => {
    const useCase = new PublishSnapshotUseCase(
      mockCollector,
      mockValidator,
      mockClient,
      memoryWorkflow,
      documentationDirectory
    );

    const result = await useCase.execute({
      agent: "codex-cli",
      repository: "/repo",
      projectKey: "catalog",
      environment: "staging",
      deploymentId: "dep-1",
      version: "1.0.0",
      model: "gpt-5",
      effort: "high",
      headRef: "HEAD",
      dryRun: true,
    });

    expect(result.status).toBe("DRY_RUN");
    expect(result.payloadSha256).toBe("hash-abc");
    expect(mockClient.publish).not.toHaveBeenCalled();
  });

  it("publishes and returns result when dryRun is false", async () => {
    const useCase = new PublishSnapshotUseCase(
      mockCollector,
      mockValidator,
      mockClient,
      memoryWorkflow,
      documentationDirectory
    );
    const progress: Array<{ phase: string; state: string }> = [];

    const result = await useCase.execute({
      repository: "/repo",
      projectKey: "catalog",
      environment: "staging",
      deploymentId: "dep-1",
      version: "1.0.0",
      agent: "claude-cli",
      model: "gpt-5",
      effort: "high",
      headRef: "HEAD",
      dryRun: false,
      apiUrl: "https://api.example.com",
      token: "secret-token",
    }, (event) => progress.push(event));

    expect(result.status).toBe("ACTIVATED");
    expect(progress).toEqual([
      { phase: "Checking publication settings", state: "started" },
      { phase: "Checking publication settings", state: "completed" },
      { phase: "Validating publication target", state: "started" },
      { phase: "Validating publication target", state: "completed" },
      { phase: "Collecting repository context", state: "started" },
      { phase: "Collecting repository context", state: "completed" },
      { phase: "Selecting documentation flow", state: "started" },
      { phase: "Selecting documentation flow", state: "completed" },
      { phase: "Fetching previous snapshot and building knowledge graph", state: "started" },
      { phase: "Fetching previous snapshot and building knowledge graph", state: "completed" },
      { phase: "Validating knowledge graph", state: "started" },
      { phase: "Validating knowledge graph", state: "completed" },
      { phase: "Publishing snapshot", state: "started" },
      { phase: "Publishing snapshot", state: "completed" },
    ]);
    expect(mockLlm.run).toHaveBeenCalledWith(
      expect.objectContaining({ agent: "claude-cli", model: "gpt-5" })
    );
    expect(mockClient.publish).toHaveBeenCalledWith(
      expect.objectContaining({
        apiUrl: "https://api.example.com",
        token: "secret-token",
        projectKey: "catalog",
        environment: "staging",
        tenantId: "b0377492-0f1c-4a7e-ab65-e30c2424fd57",
      })
    );
    expect(mockClient.validateTarget).toHaveBeenCalledWith(expect.objectContaining({
      apiUrl: "https://api.example.com",
      token: "secret-token",
      projectKey: "catalog",
      environment: "staging",
      deploymentId: "dep-1",
      version: "1.0.0",
    }));
  });

  it("requires the documented memory workflow for programmatic publication", async () => {
    const collector = { collect: vi.fn() };
    const useCase = new PublishSnapshotUseCase(collector, mockValidator, mockClient);

    await expect(useCase.execute({ agent: "codex-cli", repository: "/repo", projectKey: "catalog",
      environment: "staging", deploymentId: "dep-1", version: "1", model: "gpt-5",
      effort: "high", headRef: "HEAD", dryRun: true }))
      .rejects.toThrow("Documented memory workflow and documentation directory are required");
    expect(collector.collect).not.toHaveBeenCalled();
  });

  it("reports a failed phase and preserves its error", async () => {
    const collector: GitContextCollectorPort = {
      collect: vi.fn().mockRejectedValue(new Error("Git context unavailable")),
    };
    const useCase = new PublishSnapshotUseCase(collector, mockValidator, mockClient,
      memoryWorkflow, documentationDirectory);
    const progress: Array<{ phase: string; state: string }> = [];

    await expect(useCase.execute({
      repository: "/repo",
      projectKey: "catalog",
      environment: "staging",
      deploymentId: "dep-1",
      version: "1.0.0",
      agent: "claude-cli",
      model: "gpt-5",
      effort: "high",
      headRef: "HEAD",
      dryRun: true,
    }, (event) => progress.push(event))).rejects.toThrow("Git context unavailable");

    expect(progress).toEqual([
      { phase: "Checking publication settings", state: "started" },
      { phase: "Checking publication settings", state: "completed" },
      { phase: "Collecting repository context", state: "started" },
      { phase: "Collecting repository context", state: "failed" },
    ]);
  });

  it("rejects a programmatic call without an agent before collecting context", async () => {
    const collector = { collect: vi.fn() };
    const useCase = new PublishSnapshotUseCase(collector, mockValidator, mockClient,
      memoryWorkflow, documentationDirectory);
    await expect(useCase.execute({ repository: "/repo", projectKey: "catalog",
      environment: "staging", deploymentId: "dep-1", version: "1", model: "gpt-5",
      effort: "high", headRef: "HEAD", dryRun: true })).rejects.toThrow("agent is required");
    expect(collector.collect).not.toHaveBeenCalled();
  });

  it("uses the global API key when a programmatic caller omits a token", async () => {
    vi.stubEnv("HARNESS_MEMORY_API_KEY", "global-key");
    try {
      const useCase = new PublishSnapshotUseCase(mockCollector, mockValidator, mockClient,
        memoryWorkflow, documentationDirectory);
      await useCase.execute({ agent: "codex-cli", repository: "/repo", projectKey: "catalog", environment: "staging",
        deploymentId: "dep-1", version: "1", model: "gpt-5", effort: "high",
        headRef: "HEAD", dryRun: false, apiUrl: "https://api.example.com" });
      expect(mockClient.publish).toHaveBeenCalledWith(expect.objectContaining({ token: "global-key" }));
    } finally {
      vi.unstubAllEnvs();
    }
  });

  it("rejects a repository without docs and directs users to project-memory", async () => {
    const graph = { schema_version: "1.0", entities: [], relations: [], evidence: [] };
    const existing = { run: vi.fn().mockResolvedValue({ status: "READY", graph }) };
    const directory = { exists: vi.fn().mockReturnValue(false) };
    const useCase = new PublishSnapshotUseCase(mockCollector, mockValidator, mockClient,
      existing, directory);
    const progress: Array<{ phase: string; state: string }> = [];

    await expect(useCase.execute({ agent: "codex-cli", repository: "/repo", projectKey: "catalog",
      environment: "staging", deploymentId: "dep-1", version: "1", model: "gpt-5",
      effort: "high", headRef: "HEAD", dryRun: true }, event => progress.push(event)))
      .rejects.toThrow(/project has no documentation.*project-memory.*https:\/\/github.com\/romabeckman\/harness-kit/i);

    expect(directory.exists).toHaveBeenCalledWith("/repo");
    expect(existing.run).not.toHaveBeenCalled();
    expect(mockClient.publish).not.toHaveBeenCalled();
    expect(progress).toContainEqual({ phase: "Selecting documentation flow", state: "failed" });
  });

  it("routes a repository with docs through the existing documentation phase", async () => {
    const graph = { schema_version: "1.0", entities: [], relations: [], evidence: [] };
    const existing = { run: vi.fn().mockResolvedValue({ status: "READY", graph }) };
    const directory = { exists: vi.fn().mockReturnValue(true) };
    const useCase = new PublishSnapshotUseCase(mockCollector, mockValidator, mockClient,
      existing, directory);

    await useCase.execute({ agent: "codex-cli", repository: "/repo", projectKey: "catalog",
      environment: "staging", deploymentId: "dep-1", version: "1", model: "gpt-5",
      effort: "high", headRef: "HEAD", dryRun: true });

    expect(existing.run).toHaveBeenCalledOnce();
  });

  it("validates options before inspecting the documentation directory", async () => {
    const directory = { exists: vi.fn() };
    const workflow = { run: vi.fn() };
    const useCase = new PublishSnapshotUseCase(mockCollector, mockValidator, mockClient,
      workflow, directory);

    await expect(useCase.execute({ agent: "codex-cli", repository: "", projectKey: "",
      environment: "staging", deploymentId: "dep-1", version: "1", model: "gpt-5",
      effort: "high", headRef: "HEAD", dryRun: true })).rejects.toThrow(ConfigurationError);

    expect(directory.exists).not.toHaveBeenCalled();
  });
});
