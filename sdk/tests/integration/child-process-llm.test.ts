import { describe, expect, it } from "vitest";
import { LocalLlmRunner } from "../../src/infrastructure/llm/local-llm-runner.js";
import { GraphValidator } from "../../src/infrastructure/validator/graph-validator.js";
import { RepositoryContext } from "../../src/application/ports/git-context-collector.port.js";

describe("Child process LLM integration", () => {
  const runner = new LocalLlmRunner();
  const validator = new GraphValidator();

  const dummyContext: RepositoryContext = {
    commitSha: "8f05d8c1234567890abcdef1234567890abcdef1",
    headRef: "HEAD",
    files: [
      {
        path: "src/payments.ts",
        content: "export class PaymentProcessor {}",
        sha256: "hash-processor",
      },
    ],
    diffs: [],
  };

  it("ensures HARNESS_MEMORY_API_KEY is stripped from child environment and parses graph output", async () => {
    // Fake LLM script in node that checks process.env for token, reads stdin, and writes valid graph
    const fakeLlmScript = `
      const fs = require('fs');
      if (process.env.HARNESS_MEMORY_API_KEY || process.env.API_ADMIN_TOKEN) {
        process.stderr.write("LEAKED_TOKEN");
        process.exit(99);
      }
      process.stdin.resume();
      let input = '';
      process.stdin.on('data', chunk => { input += chunk; });
      process.stdin.on('end', () => {
        const payload = JSON.parse(input);
        if (!payload.project_key) {
          process.exit(1);
        }
        const doc = {
          schema_version: '1.0',
          entities: [
            { key: 'feature:payments', type: 'feature', name: 'Payments' },
            { key: 'adr:payments', type: 'adr', name: 'Payments Decision' }
          ],
          relations: [
            {
              ref: 'payments-owns-api',
              source_entity_key: 'feature:payments',
              type: 'references',
              target_entity_key: 'adr:payments',
              provenance: 'declared'
            }
          ],
          evidence: [
            { source: 'src/payments.ts:1', relation_ref: 'payments-owns-api' }
          ]
        };
        process.stdout.write(JSON.stringify(doc));
      });
    `;

    // Temporarily set tokens in process.env to verify they are NOT passed
    process.env.HARNESS_MEMORY_API_KEY = "super-secret-token";
    process.env.API_ADMIN_TOKEN = "super-admin-secret";

    try {
      const doc = await runner.run({
        agent: "codex-cli",
        model: "codex",
        effort: "high",
        llmCommand: process.execPath,
        timeoutSeconds: 10,
        projectKey: "payments",
        environment: "production",
        context: dummyContext,
        commandArgs: ["-e", fakeLlmScript],
      });

      expect(doc.schema_version).toBe("1.0");
      const validated = validator.validateAndCanonicalize(doc);
      expect(validated.counts).toEqual({ entities: 2, relations: 1, evidence: 1 });
      expect(validated.document.entities[0].key).toBe("adr:payments");
      expect(validated.document.entities[1].key).toBe("feature:payments");
    } finally {
      delete process.env.HARNESS_MEMORY_API_KEY;
      delete process.env.API_ADMIN_TOKEN;
    }
  });
});
