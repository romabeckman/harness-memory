export const ExitCode = {
  SUCCESS: 0,
  USAGE_OR_CONFIG: 2,
  CONTEXT_COLLECTION: 3,
  LLM_EXECUTION: 4,
  VALIDATION: 5,
  API_AUTH: 6,
  CONFLICT: 7,
  API_SERVER_OR_RETRY_EXHAUSTED: 8,
  INTERRUPTED: 130,
} as const;

export type ExitCode = (typeof ExitCode)[keyof typeof ExitCode];
