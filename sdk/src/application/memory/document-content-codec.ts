import { GraphDocument, EntityFact } from "../../domain/contracts.js";
import { GraphValidationError } from "../../domain/graph-validation-error.js";
import { digest } from "./memory-graph.js";

/** Complete Markdown is stored in bounded graph nodes, never truncated. */
export class DocumentContentCodec {
  encode(input: GraphDocument): GraphDocument {
    const graph = structuredClone(input);
    const sections: EntityFact[] = [];
    for (const entity of graph.entities) {
      const content = entity.metadata?.content;
      if (typeof content !== "string") continue;
      entity.metadata!.content_sha256 = digest(content);
      if (Buffer.byteLength(JSON.stringify(entity.metadata)) <= 48000) continue;
      const chunks: string[] = [];
      let chunk = "";
      let count = 0;
      for (const character of content) {
        chunk += character;
        if (++count === 4000) { chunks.push(chunk); chunk = ""; count = 0; }
      }
      if (chunk) chunks.push(chunk);
      const keys = chunks.map((text, index) => {
        const key = `document_section:${digest(`${entity.key}|${index}|${text}`).slice(0, 40)}`;
        sections.push({ key, type: "document_section", name: `${entity.name ?? entity.key} (${index + 1})`.slice(0, 255),
          metadata: { document_key: entity.key, index, content: text, content_sha256: digest(text) } });
        graph.relations.push({ ref: `section:${digest(key + entity.key).slice(0, 40)}`, source_entity_key: key,
          target_entity_key: entity.key, type: "part_of", provenance: "declared" });
        return key;
      });
      delete entity.metadata!.content;
      entity.metadata!.content_parts = keys;
    }
    graph.entities.push(...sections);
    return graph;
  }

  decode(input: GraphDocument): GraphDocument {
    if (!input || !Array.isArray(input.entities) || !Array.isArray(input.relations) || !Array.isArray(input.evidence)) throw new GraphValidationError("Invalid memory graph arrays");
    const graph = structuredClone(input);
    const sections = new Map(graph.entities.filter(e => e.type === "document_section").map(e => [e.key, e]));
    let bytes = 0;
    for (const entity of graph.entities) {
      const parts = entity.metadata?.content_parts;
      if (parts === undefined) continue;
      if (!Array.isArray(parts) || new Set(parts).size !== parts.length) throw new GraphValidationError("Invalid document section list");
      const content = parts.map((key, index) => {
        const section = sections.get(key);
        const text = section?.metadata?.content;
        if (typeof text !== "string" || section?.metadata?.document_key !== entity.key || section.metadata.index !== index || digest(text) !== section.metadata.content_sha256) {
          throw new GraphValidationError(`Missing or corrupt document section: ${key}`);
        }
        bytes += Buffer.byteLength(text);
        if (bytes > 50 * 1024 * 1024) throw new GraphValidationError("Document sections exceed memory budget");
        return text;
      }).join("");
      if (digest(content) !== entity.metadata!.content_sha256) throw new GraphValidationError("Document section checksum mismatch");
      entity.metadata!.content = content;
      delete entity.metadata!.content_parts;
    }
    graph.entities = graph.entities.filter(e => e.type !== "document_section");
    graph.relations = graph.relations.filter(r => !sections.has(r.source_entity_key) && !sections.has(r.target_entity_key));
    const refs = new Set(graph.relations.map(r => r.ref));
    graph.evidence = graph.evidence.filter(e => !e.relation_ref || refs.has(e.relation_ref));
    return graph;
  }
}
