import { readFileSync } from "node:fs";
import { PROJECT_MEMORY_PROMPT } from "../../application/memory/project-memory-prompt.js";

const RESOURCES = [
  "SKILL.md",
  "references/ARCHITECTURE-RULES.md",
  "references/TESTS-RULES.md",
  "references/README-RULES.md",
  "references/DOCUMENT-TEMPLATE.md",
  "scripts/generate_docs_graph.py",
];

export class BundledProjectMemorySkill {
  public load(): string {
    const root = new URL("../../../skills/project-memory/", import.meta.url);
    const resources = RESOURCES.map(path =>
      `<skill_resource path="${path}">\n${readFileSync(new URL(path, root), "utf8")}\n</skill_resource>`).join("\n");
    return `${PROJECT_MEMORY_PROMPT}\n` +
      `<bundled_project_memory_skill>\n${resources}\n</bundled_project_memory_skill>\n` +
      `<sdk_bootstrap_contract>The bundled skill supplies documentation structure and content rules. ` +
      `First use source summaries to map architecture and features. Then emit all required ADR, feature, README, ` +
      `and digest content as document entities in one JSON graph. Do not call tools, run scripts, ask questions, ` +
      `or write workspace files. The SDK creates .docs/, generates docs/.graph.json, validates the graph, and writes ` +
      `final docs/. Treat the skill's file-writing and delivery steps as output requirements implemented by the SDK. ` +
      `Return only the schema_version 1.0 JSON graph.</sdk_bootstrap_contract>`;
  }
}
