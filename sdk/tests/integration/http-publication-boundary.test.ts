import { createServer, Server } from "node:http";
import { describe, expect, it, afterEach, beforeEach } from "vitest";
import { RestPublicationClient } from "../../src/infrastructure/api/rest-publication-client.js";
import { PublishRequest } from "../../src/application/ports/publication-client.port.js";

describe("HTTP publication boundary integration", () => {
  let server: Server;
  let serverUrl: string;
  let receivedRequests: Array<{ method: string; url: string; headers: any; body: any }>;

  beforeEach(async () => {
    receivedRequests = [];
    server = createServer((req, res) => {
      let data = "";
      req.on("data", (chunk) => {
        data += chunk;
      });
      req.on("end", () => {
        const body = data ? JSON.parse(data) : null;
        receivedRequests.push({
          method: req.method || "",
          url: req.url || "",
          headers: req.headers,
          body,
        });

        if (req.url === "/v1/knowledge-publications") {
          res.writeHead(201, { "Content-Type": "application/json" });
          res.end(
            JSON.stringify({
              status: "ACTIVATED",
              publication_id: "pub-001",
              snapshot_id: "snap-001",
              project_key: body.project_key,
              environment: body.environment,
              deployment_id: body.deployment_id,
              version: body.version,
            })
          );
        } else {
          res.writeHead(404);
          res.end();
        }
      });
    });

    await new Promise<void>((resolve) => {
      server.listen(0, "127.0.0.1", () => {
        const addr = server.address() as any;
        serverUrl = `http://127.0.0.1:${addr.port}`;
        resolve();
      });
    });
  });

  afterEach(async () => {
    await new Promise<void>((resolve) => server.close(() => resolve()));
  });

  it("sends authenticated request with exact graph and NO tenant_id", async () => {
    const client = new RestPublicationClient();
    const request: PublishRequest = {
      apiUrl: serverUrl,
      token: "secret-bearer-token",
      projectKey: "payments",
      environment: "staging",
      deploymentId: "deploy-789",
      version: "1.0.0",
      graph: {
        document: {
          schema_version: "1.0",
          entities: [{ key: "service:payments", type: "service" }],
          relations: [],
          evidence: [],
        },
        canonicalJson: "{}",
        sha256: "hash-789",
        counts: { entities: 1, relations: 0, evidence: 0 },
      },
    };

    const result = await client.publish(request);
    expect(result.status).toBe("ACTIVATED");
    expect(result.publicationId).toBe("pub-001");

    expect(receivedRequests).toHaveLength(1);
    const req = receivedRequests[0];
    expect(req.headers.authorization).toBe("Bearer secret-bearer-token");
    expect(req.body.project_key).toBe("payments");
    expect(req.body.environment).toBe("staging");
    expect(req.body.deployment_id).toBe("deploy-789");
    expect(req.body.version).toBe("1.0.0");
    // Verify tenant_id is NOT in the payload
    expect(req.body.tenant_id).toBeUndefined();
    expect(req.body.tenant).toBeUndefined();
  });
});
