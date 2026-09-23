import { describe, expect, it, vi } from "vitest";
import { CollectContextPhase } from "../../../../src/application/publish-snapshot/phases/collect-context-phase.js";
import { GenerateWithDocsPhase } from "../../../../src/application/publish-snapshot/phases/generate-with-docs-phase.js";
import { PublishPhase } from "../../../../src/application/publish-snapshot/phases/publish-phase.js";
import { ValidateGraphPhase } from "../../../../src/application/publish-snapshot/phases/validate-graph-phase.js";
import { ValidateOptionsPhase } from "../../../../src/application/publish-snapshot/phases/validate-options-phase.js";
import { ValidatePublicationTargetPhase } from "../../../../src/application/publish-snapshot/phases/validate-publication-target-phase.js";
import { PublishSnapshotOptions } from "../../../../src/domain/contracts.js";

const options: PublishSnapshotOptions = {
  agent: "codex-cli",
  repository: "/repo",
  projectKey: "catalog",
  environment: "staging",
  deploymentId: "deploy-1",
  version: "1",
  model: "gpt-5",
  effort: "high",
  headRef: "HEAD",
  dryRun: false,
  apiUrl: "https://example.com",
  token: "key",
};

describe("snapshot publication phases", () => {
  it("runs each phase in order and publishes the validated graph", async () => {
    const calls: string[] = [];
    const repositoryContext = { commitSha: "abc", headRef: "HEAD", files: [], diffs: [] };
    const document = { schema_version: "1.0", entities: [], relations: [], evidence: [] };
    const validatedGraph = {
      document, canonicalJson: "{}", sha256: "hash",
      counts: { entities: 0, relations: 0, evidence: 0 },
    };
    const collector = { collect: vi.fn(async () => { calls.push("collect"); return repositoryContext; }) };
    const runner = { run: vi.fn(async () => { calls.push("generate"); return { status: "READY" as const, graph: document }; }) };
    const validator = { validateAndCanonicalize: vi.fn(() => {
      calls.push("validate graph"); return validatedGraph;
    }) };
    const result = { status: "ACTIVATED" as const, projectKey: "catalog",
      environment: "staging", deploymentId: "deploy-1", version: "1", payloadSha256: "hash" };
    const client = {
      validateTarget: vi.fn(async () => { calls.push("validate target");
        return "b0377492-0f1c-4a7e-ab65-e30c2424fd57"; }),
      publish: vi.fn(async () => { calls.push("publish"); return result; }),
    };
    const first = new ValidateOptionsPhase();
    first.setNext(new ValidatePublicationTargetPhase(client))
      .setNext(new CollectContextPhase(collector))
      .setNext(new GenerateWithDocsPhase(runner))
      .setNext(new ValidateGraphPhase(validator))
      .setNext(new PublishPhase(client));

    expect(await first.handle({ options })).toEqual(result);
    expect(calls).toEqual(["validate target", "collect", "generate", "validate graph", "publish"]);
    expect(client.publish).toHaveBeenCalledWith(expect.objectContaining({ graph: validatedGraph }));
    expect(client.publish).toHaveBeenCalledWith(expect.objectContaining({
      tenantId: "b0377492-0f1c-4a7e-ab65-e30c2424fd57",
    }));
    expect(runner.run).toHaveBeenCalledWith(expect.objectContaining({
      tenantId: "b0377492-0f1c-4a7e-ab65-e30c2424fd57",
    }), repositoryContext);
  });

  it("stops before publication for dry runs", async () => {
    const document = { schema_version: "1.0", entities: [], relations: [], evidence: [] };
    const collector = { collect: vi.fn(async () => ({ commitSha: "abc", headRef: "HEAD", files: [], diffs: [] })) };
    const runner = { run: vi.fn(async () => ({ status: "READY" as const, graph: document })) };
    const validator = { validateAndCanonicalize: vi.fn(() => ({ document,
      canonicalJson: "{}", sha256: "hash", counts: { entities: 0, relations: 0, evidence: 0 } })) };
    const client = { validateTarget: vi.fn(), publish: vi.fn() };
    const first = new ValidateOptionsPhase();
    first.setNext(new ValidatePublicationTargetPhase(client))
      .setNext(new CollectContextPhase(collector))
      .setNext(new GenerateWithDocsPhase(runner))
      .setNext(new ValidateGraphPhase(validator))
      .setNext(new PublishPhase(client));

    const result = await first.handle({ options: { ...options, dryRun: true, apiUrl: undefined, token: undefined } });
    expect(result.status).toBe("DRY_RUN");
    expect(client.validateTarget).not.toHaveBeenCalled();
    expect(client.publish).not.toHaveBeenCalled();
  });

  it("stops before repository collection when target validation fails", async () => {
    const collector = { collect: vi.fn() };
    const validator = { validateAndCanonicalize: vi.fn() };
    const client = {
      validateTarget: vi.fn().mockRejectedValue(new Error("Project key not found")),
      publish: vi.fn(),
    };
    const first = new ValidateOptionsPhase();
    first.setNext(new ValidatePublicationTargetPhase(client))
      .setNext(new CollectContextPhase(collector));

    await expect(first.handle({ options })).rejects.toThrow("Project key not found");
    expect(collector.collect).not.toHaveBeenCalled();
    expect(client.publish).not.toHaveBeenCalled();
  });
});
