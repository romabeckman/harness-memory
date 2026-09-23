import { describe, expect, it, vi } from "vitest";
import { PublicationBaselineClient } from "../../../../src/infrastructure/api/publication-baseline-client.js";

describe("PublicationBaselineClient", () => {
  it("treats only 404 as an absent baseline", async () => {
    for (const status of [401, 403, 500]) {
      const client = new PublicationBaselineClient(vi.fn().mockResolvedValue(new Response("", { status })));
      await expect(client.load("https://memory.test", "secret", "project", "dev")).rejects.toThrow();
    }
    const client = new PublicationBaselineClient(vi.fn().mockResolvedValue(new Response("", { status: 404 })));
    await expect(client.load("https://memory.test", "secret", "project", "dev")).resolves.toBeUndefined();
  });

  it("rejects a successful response without a graph", async () => {
    const client = new PublicationBaselineClient(vi.fn().mockResolvedValue(Response.json({})));
    await expect(client.load("https://memory.test", "secret", "project", "dev")).rejects.toThrow("Invalid publication baseline");
  });

  it("scopes the request and returns the stored graph", async () => {
    const graph = { schema_version: "1.0", entities: [], relations: [], evidence: [] };
    const fetchFn = vi.fn().mockResolvedValue(Response.json({ graph }));
    await expect(new PublicationBaselineClient(fetchFn).load("https://memory.test", "secret", "a/b", "staging")).resolves.toEqual(graph);
    const [url, options] = fetchFn.mock.calls[0];
    expect(url.searchParams.get("project_key")).toBe("a/b");
    expect(url.searchParams.get("environment")).toBe("staging");
    expect(options.headers.Authorization).toBe("Bearer secret");
    expect(options.redirect).toBe("error");
  });
});
