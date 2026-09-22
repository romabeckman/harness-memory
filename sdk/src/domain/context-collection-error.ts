import { ExitCode } from "./exit-code.js";
import { PublisherError } from "./publisher-error.js";

export class ContextCollectionError extends PublisherError {
  public readonly exitCode = ExitCode.CONTEXT_COLLECTION;
}
