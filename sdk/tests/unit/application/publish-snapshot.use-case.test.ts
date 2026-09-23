import { describe, expect, it, vi } from "vitest";
import { PublishSnapshotUseCase } from "../../../src/application/publish-snapshot/publish-snapshot.use-case.js";
import { ConfigurationError } from "../../../src/domain/configuration-error.js";
import { GitContextCollectorPort } from "../../../src/application/ports/git-context-collector.port.js";
import { LlmRunnerPort } from "../../../src/application/ports/llm-runner.port.js";
import { GraphValidatorPort } from "../../../src/application/ports/graph-validator.port.js";
import { PublicationClientPort } from "../../../src/application/ports/publication-client.port.js";

describe("PublishSnapshotUseCase", () => {
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

  it("throws ConfigurationError when required fields are missing", async () => {
    const useCase = new PublishSnapshotUseCase(
      mockCollector,
      mockLlm,
      mockValidator,
      mockClient
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
      mockLlm,
      mockValidator,
      mockClient
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
      mockLlm,
      mockValidator,
      mockClient
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
      { phase: "Collecting repository context", state: "started" },
      { phase: "Collecting repository context", state: "completed" },
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
      })
    );
  });

  it("reports a failed phase and preserves its error", async () => {
    const collector: GitContextCollectorPort = {
      collect: vi.fn().mockRejectedValue(new Error("Git context unavailable")),
    };
    const useCase = new PublishSnapshotUseCase(collector, mockLlm, mockValidator, mockClient);
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
    const useCase = new PublishSnapshotUseCase(collector, mockLlm, mockValidator, mockClient);
    await expect(useCase.execute({ repository: "/repo", projectKey: "catalog",
      environment: "staging", deploymentId: "dep-1", version: "1", model: "gpt-5",
      effort: "high", headRef: "HEAD", dryRun: true })).rejects.toThrow("agent is required");
    expect(collector.collect).not.toHaveBeenCalled();
  });

  it("uses the global API key when a programmatic caller omits a token", async () => {
    vi.stubEnv("HARNESS_MEMORY_API_KEY", "global-key");
    try {
      const useCase = new PublishSnapshotUseCase(mockCollector, mockLlm, mockValidator, mockClient);
      await useCase.execute({ agent: "codex-cli", repository: "/repo", projectKey: "catalog", environment: "staging",
        deploymentId: "dep-1", version: "1", model: "gpt-5", effort: "high",
        headRef: "HEAD", dryRun: false, apiUrl: "https://api.example.com" });
      expect(mockClient.publish).toHaveBeenCalledWith(expect.objectContaining({ token: "global-key" }));
    } finally {
      vi.unstubAllEnvs();
    }
  });

  it("routes a repository without docs through the bootstrap phase", async () => {
    const graph = { schema_version: "1.0", entities: [], relations: [], evidence: [] };
    const existing = { run: vi.fn().mockResolvedValue(graph) };
    const bootstrap = { run: vi.fn().mockResolvedValue(graph) };
    const directory = { exists: vi.fn().mockReturnValue(false) };
    const useCase = new PublishSnapshotUseCase(mockCollector, mockLlm, mockValidator, mockClient,
      existing, bootstrap, directory);
    const progress: Array<{ phase: string; state: string }> = [];

    await useCase.execute({ agent: "codex-cli", repository: "/repo", projectKey: "catalog",
      environment: "staging", deploymentId: "dep-1", version: "1", model: "gpt-5",
      effort: "high", headRef: "HEAD", dryRun: true }, event => progress.push(event));

    expect(directory.exists).toHaveBeenCalledWith("/repo");
    expect(bootstrap.run).toHaveBeenCalledOnce();
    expect(existing.run).not.toHaveBeenCalled();
    expect(progress).toContainEqual({ phase: "Bootstrapping project documentation and building knowledge graph",
      state: "completed" });
  });

  it("routes a repository with docs through the existing documentation phase", async () => {
    const graph = { schema_version: "1.0", entities: [], relations: [], evidence: [] };
    const existing = { run: vi.fn().mockResolvedValue(graph) };
    const bootstrap = { run: vi.fn().mockResolvedValue(graph) };
    const directory = { exists: vi.fn().mockReturnValue(true) };
    const useCase = new PublishSnapshotUseCase(mockCollector, mockLlm, mockValidator, mockClient,
      existing, bootstrap, directory);

    await useCase.execute({ agent: "codex-cli", repository: "/repo", projectKey: "catalog",
      environment: "staging", deploymentId: "dep-1", version: "1", model: "gpt-5",
      effort: "high", headRef: "HEAD", dryRun: true });

    expect(existing.run).toHaveBeenCalledOnce();
    expect(bootstrap.run).not.toHaveBeenCalled();
  });

  it("validates options before inspecting the documentation directory", async () => {
    const directory = { exists: vi.fn() };
    const workflow = { run: vi.fn() };
    const useCase = new PublishSnapshotUseCase(mockCollector, mockLlm, mockValidator, mockClient,
      workflow, workflow, directory);

    await expect(useCase.execute({ agent: "codex-cli", repository: "", projectKey: "",
      environment: "staging", deploymentId: "dep-1", version: "1", model: "gpt-5",
      effort: "high", headRef: "HEAD", dryRun: true })).rejects.toThrow(ConfigurationError);

    expect(directory.exists).not.toHaveBeenCalled();
  });
});
