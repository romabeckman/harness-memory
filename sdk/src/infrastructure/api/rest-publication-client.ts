import {
  PublicationClientPort,
  PublicationTargetRequest,
  PublishRequest,
} from "../../application/ports/publication-client.port.js";
import { PublicationResult } from "../../domain/contracts.js";
import { ApiAuthError } from "../../domain/api-auth-error.js";
import { DeploymentConflictError } from "../../domain/deployment-conflict-error.js";
import { GraphValidationError } from "../../domain/graph-validation-error.js";
import { ApiServerError } from "../../domain/api-server-error.js";
import { ConfigurationError } from "../../domain/configuration-error.js";

export interface RestClientOptions {
  maxRetries?: number;
  baseDelayMs?: number;
  maxDelayMs?: number;
  timeoutMs?: number;
  fetchFn?: typeof fetch;
}

const UUID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

export class RestPublicationClient implements PublicationClientPort {
  private readonly maxRetries: number;
  private readonly baseDelayMs: number;
  private readonly maxDelayMs: number;
  private readonly timeoutMs: number;
  private readonly fetchFn: typeof fetch;

  constructor(options?: RestClientOptions) {
    this.maxRetries = options?.maxRetries ?? 3;
    this.baseDelayMs = options?.baseDelayMs ?? 1000;
    this.maxDelayMs = options?.maxDelayMs ?? 15000;
    this.timeoutMs = options?.timeoutMs ?? 30000;
    this.fetchFn = options?.fetchFn ?? ((...args) => fetch(...args));
  }

  public async validateTarget(request: PublicationTargetRequest): Promise<string> {
    const apiUrl = this.validateAndNormalizeUrl(request.apiUrl);
    this.validateTargetValues(request);

    const projectsUrl = this.createSearchUrl(apiUrl, "/v1/projects", {
      key: request.projectKey,
      limit: "2",
      ...(request.tenantId ? { tenant_id: request.tenantId } : {}),
    });
    const projects = await this.fetchCollection(projectsUrl, request.token, "project search");
    if (projects.length === 0) {
      throw new ConfigurationError(
        `Project key '${request.projectKey}' was not found. Create the project before publishing.`
      );
    }
    if (projects.length > 1) {
      throw new ConfigurationError(
        `Project key '${request.projectKey}' matches multiple tenants. Specify --tenant-id.`
      );
    }
    const tenantId = projects[0].tenant_id;
    if (typeof tenantId !== "string" || !UUID_PATTERN.test(tenantId)) {
      throw new ApiServerError("Project search response is missing a valid tenant_id");
    }

    const environmentsUrl = this.createSearchUrl(apiUrl, "/v1/environments", {
      project_key: request.projectKey,
      name: request.environment,
      tenant_id: tenantId,
      limit: "2",
    });
    const environments = await this.fetchCollection(
      environmentsUrl,
      request.token,
      "environment search"
    );
    if (environments.length > 1) {
      throw new ConfigurationError(
        `Environment '${request.environment}' is ambiguous for project '${request.projectKey}'. Specify --tenant-id.`
      );
    }

    const publicationsUrl = this.createSearchUrl(apiUrl, "/v1/knowledge-publications", {
      project_key: request.projectKey,
      environment: request.environment,
      deployment_id: request.deploymentId,
      tenant_id: tenantId,
      limit: "2",
    });
    const publications = await this.fetchCollection(
      publicationsUrl,
      request.token,
      "deployment search"
    );
    if (publications.length > 1) {
      throw new ConfigurationError(
        `Deployment ID '${request.deploymentId}' is ambiguous for this target. Specify --tenant-id.`
      );
    }
    const existingVersion = publications[0]?.version;
    if (typeof existingVersion === "string" && existingVersion !== request.version) {
      throw new DeploymentConflictError(
        `Deployment ID '${request.deploymentId}' already belongs to version '${existingVersion}'. Use a new deployment ID.`
      );
    }
    return tenantId;
  }

  public async publish(request: PublishRequest): Promise<PublicationResult> {
    const urlObj = this.validateAndNormalizeUrl(request.apiUrl);
    const targetUrl = new URL("/v1/knowledge-publications", urlObj).toString();

    const requestBody = JSON.stringify({
      tenant_id: request.tenantId,
      project_key: request.projectKey,
      environment: request.environment,
      deployment_id: request.deploymentId,
      version: request.version,
      metadata: request.graph.document.metadata ?? {},
      entities: request.graph.document.entities,
      relations: request.graph.document.relations,
      evidence: request.graph.document.evidence,
    });

    const headers = {
      Authorization: `Bearer ${request.token}`,
      "Content-Type": "application/json",
      Accept: "application/json",
    };

    let attempt = 0;
    while (true) {
      attempt++;
      try {
        const signal = AbortSignal.timeout(this.timeoutMs);
        const response = await this.fetchFn(targetUrl, {
          method: "POST",
          headers,
          body: requestBody,
          signal,
        });

        if (response.status === 201) {
          const body: any = await response.json();
          return {
            status: "ACTIVATED",
            publicationId: body.publication_id || body.id,
            snapshotId: body.snapshot_id,
            projectKey: request.projectKey,
            environment: request.environment,
            deploymentId: request.deploymentId,
            version: request.version,
            payloadSha256: request.graph.sha256,
            counts: request.graph.counts,
          };
        }

        if (response.status === 200) {
          const body: any = await response.json();
          return {
            status: "ALREADY_PUBLISHED",
            publicationId: body.publication_id || body.id,
            snapshotId: body.snapshot_id,
            projectKey: request.projectKey,
            environment: request.environment,
            deploymentId: request.deploymentId,
            version: request.version,
            payloadSha256: request.graph.sha256,
            counts: request.graph.counts,
          };
        }

        if (response.status === 401 || response.status === 403) {
          const text = await response.text();
          throw new ApiAuthError(
            `Authentication failed (${response.status}): ${this.redact(text)}`
          );
        }

        if (response.status === 409) {
          const text = await response.text();
          throw new DeploymentConflictError(
            `Deployment conflict (409): ${this.redact(text)}`
          );
        }

        if (response.status === 404 || response.status === 422) {
          const text = await response.text();
          throw new GraphValidationError(
            `API validation rejected payload (${response.status}): ${this.redact(text)}`
          );
        }

        // Retryable status codes: 408, 429, 5xx
        const isRetryable =
          response.status === 408 ||
          response.status === 429 ||
          response.status >= 500;

        if (!isRetryable || attempt > this.maxRetries) {
          const text = await response.text();
          throw new ApiServerError(
            `API request failed with status ${response.status}: ${this.redact(text)}`
          );
        }

        const retryAfterHeader = response.headers.get("Retry-After");
        await this.delay(attempt, retryAfterHeader);
      } catch (err: any) {
        if (
          err instanceof ApiAuthError ||
          err instanceof DeploymentConflictError ||
          err instanceof GraphValidationError ||
          err instanceof ConfigurationError
        ) {
          throw err;
        }

        const isTimeout =
          err.name === "TimeoutError" ||
          err.name === "AbortError" ||
          err.message?.toLowerCase().includes("aborted") ||
          err.message?.toLowerCase().includes("timeout");

        if (attempt > this.maxRetries) {
          const detail = isTimeout
            ? `Request timed out after ${this.timeoutMs}ms (${attempt} attempts)`
            : err.message;
          throw new ApiServerError(
            `API request failed after ${attempt} attempts: ${this.redact(detail)}`
          );
        }

        await this.delay(attempt, null);
      }
    }
  }

  private validateAndNormalizeUrl(rawUrl: string): URL {
    let parsed: URL;
    try {
      parsed = new URL(rawUrl);
    } catch {
      throw new ConfigurationError(`Invalid API URL: '${rawUrl}'`);
    }

    const isLocal =
      parsed.hostname === "localhost" ||
      parsed.hostname === "127.0.0.1" ||
      parsed.hostname === "::1";

    if (!isLocal && parsed.protocol !== "https:") {
      throw new ConfigurationError(
        `HTTPS is required for non-localhost API URLs: '${rawUrl}'`
      );
    }

    return parsed;
  }

  private validateTargetValues(request: PublicationTargetRequest): void {
    if (!request.token.trim()) throw new ConfigurationError("token is required for publication target validation");
    if (request.tenantId && !UUID_PATTERN.test(request.tenantId)) {
      throw new ConfigurationError("tenant-id must be a UUID");
    }
    if (!request.projectKey.trim() || request.projectKey.length > 255) {
      throw new ConfigurationError("project-key must contain 1 to 255 characters");
    }
    if (request.projectKey !== request.projectKey.trim()) {
      throw new ConfigurationError("project-key must not contain leading or trailing whitespace");
    }
    if (
      request.environment.length > 64 ||
      !/^[a-zA-Z0-9_-]{1,64}$/.test(request.environment)
    ) {
      throw new ConfigurationError(
        "environment must contain 1 to 64 letters, numbers, underscores, or hyphens"
      );
    }
    if (!request.deploymentId.trim() || request.deploymentId.length > 255) {
      throw new ConfigurationError("deployment-id must contain 1 to 255 characters");
    }
    if (!request.version.trim() || request.version.length > 64) {
      throw new ConfigurationError("version must contain 1 to 64 characters");
    }
  }

  private createSearchUrl(apiUrl: URL, path: string, parameters: Record<string, string>): URL {
    const url = new URL(path, apiUrl);
    for (const [key, value] of Object.entries(parameters)) url.searchParams.set(key, value);
    return url;
  }

  private async fetchCollection(
    url: URL,
    token: string,
    description: string
  ): Promise<Array<Record<string, unknown>>> {
    let attempt = 0;
    while (true) {
      attempt += 1;
      try {
        const response = await this.fetchFn(url, {
          method: "GET",
          headers: { Authorization: `Bearer ${token}`, Accept: "application/json" },
          signal: AbortSignal.timeout(this.timeoutMs),
          redirect: "error",
        });
        if (response.status === 401 || response.status === 403) {
          throw new ApiAuthError(`Publication ${description} access denied (${response.status})`);
        }
        if (response.status === 408 || response.status === 429 || response.status >= 500) {
          if (attempt <= this.maxRetries) {
            await this.delay(attempt, response.headers.get("Retry-After"));
            continue;
          }
        }
        if (!response.ok) {
          throw new ApiServerError(`Publication ${description} failed (${response.status})`);
        }
        let body: unknown;
        try { body = await response.json(); }
        catch { throw new ApiServerError(`Invalid ${description} response JSON`); }
        if (!Array.isArray(body)) {
          throw new ApiServerError(`Invalid ${description} response`);
        }
        return body as Array<Record<string, unknown>>;
      } catch (error: any) {
        if (error instanceof ApiAuthError || error instanceof ApiServerError) throw error;
        if (attempt > this.maxRetries) {
          const timedOut = error?.name === "TimeoutError" || error?.name === "AbortError";
          throw new ApiServerError(
            timedOut
              ? `Publication ${description} timed out after ${attempt} attempts`
              : `Publication ${description} failed after ${attempt} attempts`
          );
        }
        await this.delay(attempt, null);
      }
    }
  }

  private async delay(attempt: number, retryAfter: string | null): Promise<void> {
    if (retryAfter) {
      const seconds = Number.parseInt(retryAfter, 10);
      if (!Number.isNaN(seconds) && seconds > 0 && seconds <= 60) {
        await new Promise((res) => setTimeout(res, seconds * 1000));
        return;
      }
    }

    // Exponential backoff with jitter
    const exp = Math.min(this.maxDelayMs, this.baseDelayMs * Math.pow(2, attempt - 1));
    const jitter = Math.random() * 0.3 * exp;
    const total = exp + jitter;
    await new Promise((res) => setTimeout(res, total));
  }

  private redact(message: string): string {
    return message
      .replace(/(bearer\s+)[A-Za-z0-9_\-\.]+/gi, "$1[REDACTED]")
      .replace(/(token|secret|password)[=:\s]+[A-Za-z0-9_\-\.]+/gi, "$1=[REDACTED]");
  }
}
