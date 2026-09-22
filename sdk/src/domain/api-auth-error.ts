import { ExitCode } from "./exit-code.js";
import { PublisherError } from "./publisher-error.js";

export class ApiAuthError extends PublisherError {
  public readonly exitCode = ExitCode.API_AUTH;
}
