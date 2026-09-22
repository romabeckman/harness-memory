#!/usr/bin/env node
import { CliApp } from "./cli-app.js";
import { ExitCode } from "../domain/exit-code.js";

process.on("SIGINT", () => {
  process.exit(ExitCode.INTERRUPTED);
});

process.on("SIGTERM", () => {
  process.exit(ExitCode.INTERRUPTED);
});

const app = new CliApp();
const exitCode = await app.run(process.argv.slice(2));
process.exit(exitCode);
