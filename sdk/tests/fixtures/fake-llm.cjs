process.stdin.resume();
let input = "";
process.stdin.on("data", (chunk) => {
  input += chunk;
});
process.stdin.on("end", () => {
  const doc = {
    schema_version: "1.0",
    entities: [],
    relations: [],
    evidence: []
  };
  process.stdout.write(JSON.stringify(doc));
});
