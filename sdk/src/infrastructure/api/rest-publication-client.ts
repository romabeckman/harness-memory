import {
  PublicationClientPort,
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

  public async publish(request: PublishRequest): Promise<PublicationResult> {
    const urlObj = this.validateAndNormalizeUrl(request.apiUrl);
    const targetUrl = new URL("/v1/knowledge-publications", urlObj).toString();

    const requestBody = JSON.stringify({
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
