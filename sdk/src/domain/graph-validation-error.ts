import { ExitCode } from "./exit-code.js";
import { PublisherError } from "./publisher-error.js";

export class GraphValidationError extends PublisherError {
  public readonly exitCode = ExitCode.VALIDATION;
}
