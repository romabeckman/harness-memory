import { describe, expect, it, vi, beforeEach } from "vitest";
import { RestPublicationClient } from "../../../../src/infrastructure/api/rest-publication-client.js";
import { ApiAuthError } from "../../../../src/domain/api-auth-error.js";
import { DeploymentConflictError } from "../../../../src/domain/deployment-conflict-error.js";
import { GraphValidationError } from "../../../../src/domain/graph-validation-error.js";
import { ApiServerError } from "../../../../src/domain/api-server-error.js";
import { ConfigurationError } from "../../../../src/domain/configuration-error.js";
import { PublishRequest } from "../../../../src/application/ports/publication-client.port.js";

describe("RestPublicationClient", () => {
  const client = new RestPublicationClient({ maxRetries: 2, baseDelayMs: 10 });

  const dummyRequest: PublishRequest = {
    apiUrl: "http://localhost:8000",
    token: "valid-token",
    projectKey: "catalog",
    environment: "staging",
    deploymentId: "dep-1",
    version: "1.0.0",
    graph: {
      document: {
        schema_version: "1.0",
        entities: [{ key: "svc-1", type: "service" }],
        relations: [],
        evidence: [],
      },
      canonicalJson: "{}",
      sha256: "hash-1",
      counts: { entities: 1, relations: 0, evidence: 0 },
    },
  };

  it("rejects non-https url outside localhost", async () => {
    await expect(
      client.publish({
        ...dummyRequest,
        apiUrl: "http://remote-harness.example.com",
      })
    ).rejects.toThrow(ConfigurationError);
  });

  it("handles 201 ACTIVATED successfully", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        status: 201,
        ok: true,
        json: async () => ({
          status: "ACTIVATED",
          publication_id: "pub-1",
          snapshot_id: "snap-1",
          project_key: "catalog",
          environment: "staging",
          deployment_id: "dep-1",
          version: "1.0.0",
        }),
      })
    );

    const result = await client.publish(dummyRequest);
    expect(result.status).toBe("ACTIVATED");
    expect(result.publicationId).toBe("pub-1");
  });

  it("sends the graph index as snapshot metadata", async () => {
    const graphIndex = { nodes: [{ id: "feature:orders", path: "docs/feature/orders.md" }], edges: [] };
    const fetchMock = vi.fn().mockResolvedValue({ status: 201, json: async () => ({ status: "ACTIVATED" }) });
    vi.stubGlobal("fetch", fetchMock);

    await client.publish({ ...dummyRequest,
      graph: { ...dummyRequest.graph, document: { ...dummyRequest.graph.document,
        metadata: graphIndex } as any } });

    expect(JSON.parse(fetchMock.mock.calls[0][1].body).metadata).toEqual(graphIndex);
  });

  it("handles 200 ALREADY_PUBLISHED successfully", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        status: 200,
        ok: true,
        json: async () => ({
          status: "ALREADY_PUBLISHED",
          project_key: "catalog",
          environment: "staging",
          deployment_id: "dep-1",
          version: "1.0.0",
        }),
      })
    );

    const result = await client.publish(dummyRequest);
    expect(result.status).toBe("ALREADY_PUBLISHED");
  });

  it("throws ApiAuthError on 401 without retry", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      status: 401,
      ok: false,
      text: async () => "Unauthorized",
    });
    vi.stubGlobal("fetch", fetchMock);

    await expect(client.publish(dummyRequest)).rejects.toThrow(ApiAuthError);
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it("throws DeploymentConflictError on 409 without retry", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      status: 409,
      ok: false,
      text: async () => "Conflict",
    });
    vi.stubGlobal("fetch", fetchMock);

    await expect(client.publish(dummyRequest)).rejects.toThrow(DeploymentConflictError);
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it("throws GraphValidationError on 422 without retry", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      status: 422,
      ok: false,
      text: async () => "Unprocessable Entity",
    });
    vi.stubGlobal("fetch", fetchMock);

    await expect(client.publish(dummyRequest)).rejects.toThrow(GraphValidationError);
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it("retries 500 up to maxRetries and throws ApiServerError if exhausted", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      status: 500,
      ok: false,
      text: async () => "Internal Server Error",
    });
    vi.stubGlobal("fetch", fetchMock);

    await expect(client.publish(dummyRequest)).rejects.toThrow(ApiServerError);
    // 1 initial + 2 retries = 3 calls
    expect(fetchMock).toHaveBeenCalledTimes(3);
  });

  it("passes AbortSignal timeout to fetch call", async () => {
    let capturedSignal: AbortSignal | undefined;
    const customClient = new RestPublicationClient({
      maxRetries: 0,
      timeoutMs: 5000,
      fetchFn: async (url, init) => {
        capturedSignal = init?.signal;
        return {
          status: 201,
          ok: true,
          json: async () => ({ status: "ACTIVATED", id: "pub-1" }),
        } as any;
      },
    });

    await customClient.publish(dummyRequest);
    expect(capturedSignal).toBeDefined();
    expect(capturedSignal?.aborted).toBe(false);
  });

  it("retries on fetch timeout and throws ApiServerError with timeout detail", async () => {
    const timeoutErr = new DOMException("The operation was aborted due to timeout", "TimeoutError");
    const fetchMock = vi.fn().mockRejectedValue(timeoutErr);
    const customClient = new RestPublicationClient({
      maxRetries: 1,
      baseDelayMs: 5,
      timeoutMs: 1000,
      fetchFn: fetchMock,
    });

    await expect(customClient.publish(dummyRequest)).rejects.toThrow(/timed out after 1000ms/);
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });
});

