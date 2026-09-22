import { GraphDocument } from "../../domain/contracts.js";
import { ApiServerError } from "../../domain/api-server-error.js";
import { ApiAuthError } from "../../domain/api-auth-error.js";
import { ConfigurationError } from "../../domain/configuration-error.js";

export class PublicationBaselineClient {
  constructor(private readonly fetchFn: typeof fetch = fetch) {}

  async load(apiUrl: string, token: string, projectKey: string, environment: string): Promise<GraphDocument | undefined> {
    const url = new URL("/v1/knowledge-publications/latest", apiUrl);
    if (url.protocol !== "https:" && !(url.protocol === "http:" && ["localhost", "127.0.0.1", "[::1]"].includes(url.hostname))) {
      throw new ConfigurationError("HTTPS is required for publication baseline reads");
    }
    url.searchParams.set("project_key", projectKey);
    url.searchParams.set("environment", environment);
    const response = await this.fetchFn(url, { headers: { Authorization: `Bearer ${token}` }, signal: AbortSignal.timeout(30000), redirect: "error" });
    if (response.status === 404) return undefined;
    if (response.status === 401 || response.status === 403) throw new ApiAuthError("Publication baseline access denied");
    if (!response.ok) throw new ApiServerError(`Publication baseline read failed (${response.status})`);
    const reader = response.body?.getReader();
    if (!reader) throw new ApiServerError("Publication baseline response has no body");
    const chunks: Uint8Array[] = [];
    let bytes = 0;
    try {
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        bytes += value.byteLength;
        if (bytes > 50 * 1024 * 1024) throw new ApiServerError("Publication baseline exceeds 50 MiB");
        chunks.push(value);
      }
    } finally { await reader.cancel(); }
    let body: { graph?: GraphDocument };
    try { body = JSON.parse(Buffer.concat(chunks).toString("utf8")); }
    catch { throw new ApiServerError("Invalid publication baseline JSON"); }
    if (!body?.graph || !Array.isArray(body.graph.entities) || !Array.isArray(body.graph.relations) || !Array.isArray(body.graph.evidence)) {
      throw new ApiServerError("Invalid publication baseline graph");
    }
    return body.graph;
  }
}
