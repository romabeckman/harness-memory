process.stdin.resume();
let input = "";
process.stdin.on("data", (chunk) => {
  input += chunk;
});
process.stdin.on("end", () => {
  const doc = {
    schema_version: "1.0",
    entities: [
      { key: "service:payments", type: "service", name: "Payments" },
      { key: "api:payments", type: "api", name: "Payments API" }
    ],
    relations: [
      {
        ref: "payments-owns-api",
        source_entity_key: "service:payments",
        type: "provides",
        target_entity_key: "api:payments",
        provenance: "declared"
      }
    ],
    evidence: [
      { source: "src/payments.ts:1", relation_ref: "payments-owns-api" }
    ]
  };
  process.stdout.write(JSON.stringify(doc));
});
