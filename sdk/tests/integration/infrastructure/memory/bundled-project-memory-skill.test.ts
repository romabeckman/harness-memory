import { describe, expect, it } from "vitest";
import { BundledProjectMemorySkill } from "../../../../src/infrastructure/memory/bundled-project-memory-skill.js";

describe("BundledProjectMemorySkill", () => {
  it("loads the complete skill, references, and graph generator from the SDK package", () => {
    const prompt = new BundledProjectMemorySkill().load();

    for (const path of ["SKILL.md", "references/ARCHITECTURE-RULES.md",
      "references/TESTS-RULES.md", "references/README-RULES.md",
      "references/DOCUMENT-TEMPLATE.md", "scripts/generate_docs_graph.py"]) {
      expect(prompt).toContain(`<skill_resource path="${path}">`);
    }
    expect(prompt).toContain("First use source summaries to map architecture and features");
    expect(prompt).toContain("Do not call tools, run scripts, ask questions");
  });
});
