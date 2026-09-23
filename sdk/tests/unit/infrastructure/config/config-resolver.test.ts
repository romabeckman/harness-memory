import { describe, expect, it } from "vitest";
import { ConfigResolver } from "../../../../src/infrastructure/config/config-resolver.js";
import { ConfigurationError } from "../../../../src/domain/configuration-error.js";
import packageJson from "../../../../package.json";

describe("ConfigResolver", () => {
  const resolver = new ConfigResolver();

  it("resolves valid CLI arguments", () => {
    const rawArgs = [
      "--agent", "codex-cli",
      "--model",
      "gpt-5",
      "--effort",
      "high",
      "--environment",
      "production",
      "--project-key",
      "payments",
      "--deployment-id",
      "deploy-123",
      "--version",
      "v1.0.0",
      "--api-url",
      "http://localhost:8000",
      "--dry-run",
    ];

    const config = resolver.resolve(rawArgs, {});
    expect(config.model).toBe("gpt-5");
    expect(config.effort).toBe("high");
    expect(config.environment).toBe("production");
    expect(config.projectKey).toBe("payments");
    expect(config.deploymentId).toBe("deploy-123");
    expect(config.version).toBe("v1.0.0");
    expect(config.dryRun).toBe(true);
    expect(config.agent).toBe("codex-cli");
    expect(config.llmCommand).toBeUndefined();
  });

  it("selects an agent runner from CLI arguments independently of the model", () => {
    const config = resolver.resolve(
      [
        "--agent", "claude-cli",
        "--model", "gpt-5",
        "--effort", "high",
        "--environment", "staging",
        "--project-key", "payments",
        "--deployment-id", "deploy-123",
        "--version", "v1.0.0",
        "--dry-run",
      ],
      {}
    );

    expect(config.agent).toBe("claude-cli");
    expect(config.model).toBe("gpt-5");
  });

  it("resolves the agent runner from environment when CLI flag is absent", () => {
    const config = resolver.resolve(
      [
        "--model", "gpt-5",
        "--effort", "high",
        "--environment", "staging",
        "--project-key", "payments",
        "--deployment-id", "deploy-123",
        "--version", "v1.0.0",
        "--dry-run",
      ],
      { HARNESS_MEMORY_AGENT: "claude-cli" }
    );

    expect(config.agent).toBe("claude-cli");
  });

  it("rejects unsupported agent runner names", () => {
    expect(() => resolver.resolve(["--agent", "unknown-cli"], {})).toThrow(
      ConfigurationError
    );
  });

  it("requires an explicit agent from CLI, environment, or config", () => {
    expect(() => resolver.resolve(["--model", "gpt-5"], {})).toThrow("agent is required");
  });

  it("rejects unknown flags with ConfigurationError", () => {
    expect(() =>
      resolver.resolve(["--unknown-flag", "val"], {})
    ).toThrow(ConfigurationError);
  });

  it("rejects forbidden flags like --tenant or --tenant-id with ConfigurationError", () => {
    expect(() =>
      resolver.resolve(["--tenant", "tenant-a"], {})
    ).toThrow(ConfigurationError);

    expect(() =>
      resolver.resolve(["--tenant-id", "tenant-a"], {})
    ).toThrow(ConfigurationError);

    expect(() =>
      resolver.resolve(["--token", "secret"], {})
    ).toThrow(ConfigurationError);
  });

  it("reads token from environment variable specified by token-env", () => {
    const rawArgs = [
      "--agent", "codex-cli",
      "--model",
      "gpt-5",
      "--effort",
      "high",
      "--environment",
      "production",
      "--project-key",
      "payments",
      "--deployment-id",
      "deploy-123",
      "--version",
      "v1.0.0",
      "--api-url",
      "http://localhost:8000",
      "--token-env",
      "CUSTOM_TOKEN_VAR",
    ];

    const env = {
      CUSTOM_TOKEN_VAR: "my-custom-token-secret",
    };

    const config = resolver.resolve(rawArgs, env);
    expect(config.token).toBe("my-custom-token-secret");
  });

  it("uses HARNESS_MEMORY_API_KEY by default and accepts an explicit credential environment", () => {
    const args = ["--agent", "codex-cli", "--model", "gpt-5", "--effort", "high", "--environment", "production",
      "--project-key", "payments", "--deployment-id", "deploy-1", "--version", "1",
      "--api-url", "http://localhost:8000"];
    expect(resolver.resolve(args, { HARNESS_MEMORY_API_KEY: "default-key" }).token).toBe("default-key");
    expect(resolver.resolve([...args, "--token-env", "SUPPLIED_KEY"],
      { SUPPLIED_KEY: "user-key" }).token).toBe("user-key");
  });

  it("exposes hrns-memo as an alias of harness-memory", () => {
    expect(packageJson.bin["hrns-memo"]).toBe(packageJson.bin["harness-memory"]);
  });

  it("infers version and deployment-id from CI environment if not provided in CLI", () => {
    const rawArgs = [
      "--agent", "codex-cli",
      "--model",
      "gpt-5",
      "--effort",
      "high",
      "--environment",
      "staging",
      "--project-key",
      "payments",
      "--api-url",
      "http://localhost:8000",
    ];

    const env = {
      GITHUB_SHA: "commit-sha-from-gh",
      GITHUB_RUN_ID: "run-id-123",
      HARNESS_MEMORY_API_KEY: "token-abc",
    };

    const config = resolver.resolve(rawArgs, env);
    expect(config.version).toBe("commit-sha-from-gh");
    expect(config.deploymentId).toBe("run-id-123");
    expect(config.token).toBe("token-abc");
  });
});
