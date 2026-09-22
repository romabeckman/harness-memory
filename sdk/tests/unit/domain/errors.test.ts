import { describe, expect, it } from "vitest";
import { ExitCode } from "../../../src/domain/exit-code.js";
import { PublisherError } from "../../../src/domain/publisher-error.js";
import { ConfigurationError } from "../../../src/domain/configuration-error.js";
import { ContextCollectionError } from "../../../src/domain/context-collection-error.js";
import { LlmExecutionError } from "../../../src/domain/llm-execution-error.js";
import { GraphValidationError } from "../../../src/domain/graph-validation-error.js";
import { ApiAuthError } from "../../../src/domain/api-auth-error.js";
import { DeploymentConflictError } from "../../../src/domain/deployment-conflict-error.js";
import { ApiServerError } from "../../../src/domain/api-server-error.js";

describe("Domain Errors", () => {
  it("maps each domain error to its prescribed exit code", () => {
    const configErr = new ConfigurationError("missing model");
    expect(configErr).toBeInstanceOf(PublisherError);
    expect(configErr.exitCode).toBe(ExitCode.USAGE_OR_CONFIG);
    expect(configErr.message).toBe("missing model");

    const contextErr = new ContextCollectionError("git error");
    expect(contextErr.exitCode).toBe(ExitCode.CONTEXT_COLLECTION);

    const llmErr = new LlmExecutionError("timeout");
    expect(llmErr.exitCode).toBe(ExitCode.LLM_EXECUTION);

    const valErr = new GraphValidationError("dangling entity");
    expect(valErr.exitCode).toBe(ExitCode.VALIDATION);

    const authErr = new ApiAuthError("401 unauthorized");
    expect(authErr.exitCode).toBe(ExitCode.API_AUTH);

    const conflictErr = new DeploymentConflictError("payload mismatch");
    expect(conflictErr.exitCode).toBe(ExitCode.CONFLICT);

    const apiServerErr = new ApiServerError("retries exhausted");
    expect(apiServerErr.exitCode).toBe(ExitCode.API_SERVER_OR_RETRY_EXHAUSTED);
  });
});
