import { ExitCode } from "./exit-code.js";
import { PublisherError } from "./publisher-error.js";

export class DeploymentConflictError extends PublisherError {
  public readonly exitCode = ExitCode.CONFLICT;
}
