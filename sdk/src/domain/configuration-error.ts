import { ExitCode } from "./exit-code.js";
import { PublisherError } from "./publisher-error.js";

export class ConfigurationError extends PublisherError {
  public readonly exitCode = ExitCode.USAGE_OR_CONFIG;
}
