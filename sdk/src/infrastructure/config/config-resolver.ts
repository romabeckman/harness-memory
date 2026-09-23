import { existsSync, readFileSync } from "node:fs";
import { randomUUID } from "node:crypto";
import { resolve } from "node:path";
import { PublishSnapshotOptions } from "../../domain/contracts.js";
import { ConfigurationError } from "../../domain/configuration-error.js";
import { isLlmAgentType } from "../../domain/llm-agent.js";

const ALLOWED_FLAGS = new Set([
  "--agent",
  "--model",
  "--effort",
  "--environment",
  "--project-key",
  "--tenant-id",
  "--deployment-id",
  "--version",
  "--api-url",
  "--token-env",
  "--repository",
  "--base-ref",
  "--head-ref",
  "--llm-command",
  "--config",
  "--timeout",
  "--max-files",
  "--max-bytes",
  "--exclude-paths",
  "--dry-run",
  "--output",
  "--verbose",
  "--debug",
]);

const FORBIDDEN_FLAGS = new Set([
  "--tenant",
  "--token",
  "--prompt",
  "--interactive",
  "--database",
  "--db-url",
  "--postgres",
]);

export interface ResolvedCliConfig extends PublishSnapshotOptions {
  outputFormat: "json" | "text";
  configPath: string;
  debug: boolean;
}

export class ConfigResolver {
  public resolve(
    args: string[],
    env: Record<string, string | undefined> = process.env
  ): ResolvedCliConfig {
    const parsedCli = this.parseArgs(args);

    const configPath =
      parsedCli["--config"] ||
      env.HARNESS_MEMORY_CONFIG ||
      ".harness-memory.json";

    const fileConfig = this.loadFileConfig(configPath);

    const model =
      parsedCli["--model"] ||
      env.HARNESS_MEMORY_MODEL ||
      fileConfig.model ||
      "";

    const agent =
      parsedCli["--agent"] ||
      env.HARNESS_MEMORY_AGENT ||
      fileConfig.agent;
    if (!agent) throw new ConfigurationError("agent is required");
    if (!isLlmAgentType(agent)) {
      throw new ConfigurationError(
        `agent must be one of: codex-cli, claude-cli; received '${agent}'`
      );
    }

    const effort =
      (parsedCli["--effort"] ||
        env.HARNESS_MEMORY_EFFORT ||
        fileConfig.effort ||
        "") as any;

    const environment =
      parsedCli["--environment"] ||
      env.HARNESS_MEMORY_ENVIRONMENT ||
      fileConfig.environment ||
      "";

    const projectKey =
      parsedCli["--project-key"] ||
      env.HARNESS_MEMORY_PROJECT_KEY ||
      fileConfig.projectKey ||
      "";

    const tenantId =
      parsedCli["--tenant-id"] ||
      env.HARNESS_MEMORY_TENANT_ID ||
      fileConfig.tenantId;
    if (tenantId !== undefined &&
      (typeof tenantId !== "string" || !/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(tenantId))) {
      throw new ConfigurationError("tenant-id must be a UUID");
    }

    const deploymentId =
      parsedCli["--deployment-id"] ||
      env.HARNESS_MEMORY_DEPLOYMENT_ID ||
      fileConfig.deploymentId ||
      env.CI_PIPELINE_ID ||
      env.GITHUB_RUN_ID ||
      env.BUILD_ID ||
      env.CI_JOB_ID ||
      this.createDeploymentId(projectKey);

    const version =
      parsedCli["--version"] ||
      env.HARNESS_MEMORY_VERSION ||
      fileConfig.version ||
      env.CI_COMMIT_SHA ||
      env.GITHUB_SHA ||
      env.GIT_COMMIT ||
      "";

    const apiUrl =
      parsedCli["--api-url"] ||
      env.HARNESS_MEMORY_API_URL ||
      fileConfig.apiUrl;

    const tokenEnv =
      parsedCli["--token-env"] ||
      env.HARNESS_MEMORY_TOKEN_ENV ||
      fileConfig.tokenEnv ||
      "HARNESS_MEMORY_API_KEY";

    const token = env[tokenEnv];

    const repository =
      parsedCli["--repository"] ||
      env.HARNESS_MEMORY_REPOSITORY ||
      fileConfig.repository ||
      ".";

    const baseRef =
      parsedCli["--base-ref"] ||
      env.HARNESS_MEMORY_BASE_REF ||
      fileConfig.baseRef ||
      env.CI_MERGE_REQUEST_DIFF_BASE_SHA ||
      env.GITHUB_BASE_REF ||
      undefined;

    const headRef =
      parsedCli["--head-ref"] ||
      env.HARNESS_MEMORY_HEAD_REF ||
      fileConfig.headRef ||
      "HEAD";

    const llmCommand =
      parsedCli["--llm-command"] ||
      env.HARNESS_MEMORY_LLM_COMMAND ||
      fileConfig.llmCommand;

    const rawTimeout =
      parsedCli["--timeout"] ||
      env.HARNESS_MEMORY_TIMEOUT ||
      fileConfig.timeout ||
      "600";
    const timeout = Number.parseInt(String(rawTimeout), 10);
    if (Number.isNaN(timeout) || timeout < 1 || timeout > 3600) {
      throw new ConfigurationError(
        `--timeout must be a number between 1 and 3600; got '${rawTimeout}'`
      );
    }

    const rawMaxFiles =
      parsedCli["--max-files"] ||
      env.HARNESS_MEMORY_MAX_FILES ||
      fileConfig.maxFiles ||
      "2000";
    const maxFiles = Number.parseInt(String(rawMaxFiles), 10);

    const rawMaxBytes =
      parsedCli["--max-bytes"] ||
      env.HARNESS_MEMORY_MAX_BYTES ||
      fileConfig.maxBytes ||
      "10485760";
    const maxBytes = Number.parseInt(String(rawMaxBytes), 10);

    const rawExcludePaths: unknown = parsedCli["--exclude-paths"] ??
      env.HARNESS_MEMORY_EXCLUDE_PATHS ?? fileConfig.excludePaths;
    if (rawExcludePaths !== undefined && typeof rawExcludePaths !== "string" &&
      (!Array.isArray(rawExcludePaths) || rawExcludePaths.some((path) => typeof path !== "string"))) {
      throw new ConfigurationError("excludePaths must be a comma-separated string or an array of strings");
    }
    const excludePaths = typeof rawExcludePaths === "string"
      ? rawExcludePaths.split(",").map((path) => path.trim())
      : rawExcludePaths;

    const dryRun =
      parsedCli["--dry-run"] === "true" ||
      env.HARNESS_MEMORY_DRY_RUN === "true" ||
      fileConfig.dryRun === true;

    const verbose =
      parsedCli["--verbose"] === "true" ||
      env.HARNESS_MEMORY_VERBOSE === "true" ||
      fileConfig.verbose === true;

    const debug =
      parsedCli["--debug"] === "true" ||
      env.HARNESS_MEMORY_DEBUG === "true" ||
      fileConfig.debug === true;

    const outputRaw =
      parsedCli["--output"] ||
      env.HARNESS_MEMORY_OUTPUT ||
      (env.CI ? "json" : "text");
    const outputFormat = outputRaw === "text" ? "text" : "json";

    return {
      agent,
      model,
      effort,
      environment,
      projectKey,
      tenantId,
      deploymentId,
      version,
      apiUrl,
      token,
      repository,
      baseRef,
      headRef,
      llmCommand,
      timeout,
      maxFiles,
      maxBytes,
      excludePaths,
      dryRun,
      verbose,
      debug,
      outputFormat,
      configPath,
    };
  }

  private parseArgs(args: string[]): Record<string, string> {
    const result: Record<string, string> = {};

    for (let i = 0; i < args.length; i++) {
      const arg = args[i];
      if (!arg.startsWith("--")) {
        throw new ConfigurationError(`Unexpected positional argument: '${arg}'`);
      }

      const eqIdx = arg.indexOf("=");
      let flag: string;
      let value: string | undefined;

      if (eqIdx !== -1) {
        flag = arg.substring(0, eqIdx);
        value = arg.substring(eqIdx + 1);
      } else {
        flag = arg;
      }

      if (FORBIDDEN_FLAGS.has(flag)) {
        throw new ConfigurationError(
          `Forbidden flag '${flag}' is not permitted.`
        );
      }

      if (!ALLOWED_FLAGS.has(flag)) {
        throw new ConfigurationError(`Unknown flag: '${flag}'`);
      }

      if (flag === "--dry-run" || flag === "--verbose" || flag === "--debug") {
        result[flag] = "true";
        continue;
      }

      if (value === undefined) {
        if (i + 1 >= args.length || args[i + 1].startsWith("--")) {
          throw new ConfigurationError(`Flag '${flag}' requires a value`);
        }
        value = args[++i];
      }

      result[flag] = value;
    }

    return result;
  }

  private loadFileConfig(configPath: string): Record<string, any> {
    const fullPath = resolve(configPath);
    if (!existsSync(fullPath)) {
      return {};
    }
    try {
      const raw = readFileSync(fullPath, "utf8");
      return JSON.parse(raw);
    } catch (err: any) {
      throw new ConfigurationError(
        `Failed to parse config file at '${configPath}': ${err.message}`
      );
    }
  }

  private createDeploymentId(projectKey: string): string {
    const timestamp = new Date().toISOString().replace(/[:.]/g, "-");
    return `${projectKey}-${timestamp}-${randomUUID()}`;
  }
}
