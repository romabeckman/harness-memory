import { ExitCode } from "./exit-code.js";
import { PublisherError } from "./publisher-error.js";

export class ApiServerError extends PublisherError {
  public readonly exitCode = ExitCode.API_SERVER_OR_RETRY_EXHAUSTED;
}
