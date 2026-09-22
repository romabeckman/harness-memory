import { ExitCode } from "./exit-code.js";
import { PublisherError } from "./publisher-error.js";

export class LlmExecutionError extends PublisherError {
  public readonly exitCode = ExitCode.LLM_EXECUTION;
}
