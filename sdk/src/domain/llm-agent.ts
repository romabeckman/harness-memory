export const LLM_AGENT_TYPES = ["codex-cli", "claude-cli"] as const;

export type LlmAgentType = (typeof LLM_AGENT_TYPES)[number];

export const DEFAULT_LLM_AGENT: LlmAgentType = "codex-cli";

export function isLlmAgentType(value: unknown): value is LlmAgentType {
  return typeof value === "string" && LLM_AGENT_TYPES.includes(value as LlmAgentType);
}
