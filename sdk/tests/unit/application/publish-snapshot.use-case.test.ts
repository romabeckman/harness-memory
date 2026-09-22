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

    const result = await useCase.execute({
      repository: "/repo",
      projectKey: "catalog",
      environment: "staging",
      deploymentId: "dep-1",
      version: "1.0.0",
      model: "gpt-5",
      effort: "high",
      headRef: "HEAD",
      dryRun: false,
      apiUrl: "https://api.example.com",
      token: "secret-token",
    });

    expect(result.status).toBe("ACTIVATED");
    expect(mockClient.publish).toHaveBeenCalledWith(
      expect.objectContaining({
        apiUrl: "https://api.example.com",
        token: "secret-token",
        projectKey: "catalog",
        environment: "staging",
      })
    );
  });
});
