import { ExitCode } from "./exit-code.js";

export abstract class PublisherError extends Error {
  public abstract readonly exitCode: ExitCode;

  constructor(message: string, options?: ErrorOptions) {
    super(message, options);
    this.name = this.constructor.name;
    Object.setPrototypeOf(this, new.target.prototype);
  }
}
