process.stdin.resume();
let input = "";
process.stdin.on("data", chunk => { input += chunk; });
process.stdin.on("end", () => {
  const invocation = JSON.parse(input);
  if (invocation.instruction.includes("Summarize this source batch")) {
    process.stdout.write(JSON.stringify({ schema_version: "1.0", entities: [], relations: [], evidence: [] }));
    return;
  }
  const docs = [
    ["adr:architecture", "adr", "docs/adr/ARCHITECTURE.md",
      "---\nnode_id: \"adr:architecture\"\n---\n# Architecture\n\n## OVERVIEW\nSource architecture.\n"],
    ["adr:tests", "adr", "docs/adr/TESTS.md",
      "---\nnode_id: \"adr:tests\"\n---\n# Tests\n\n## OVERVIEW\nSource tests.\n"],
    ["feature:bootstrap", "feature", "docs/feature/bootstrap.md",
      "---\nnode_id: \"feature:bootstrap\"\n---\n# Bootstrap\n```graph\n{}\n```\n\n## OVERVIEW\nBootstrap feature.\n"],
    ["document:digest", "document", "docs/.digest.md", "# Digest\n"],
    ["document:index", "document", "docs/README.md", "# Documentation\n"],
  ];
  process.stdout.write(JSON.stringify({ schema_version: "1.0", entities: docs.map(([key, type, path, content]) =>
    ({ key, type, name: key, metadata: { path, content } })), relations: [], evidence: [] }));
});
