import { createHash } from "node:crypto";
import {
  ALLOWED_ENTITY_TYPES,
  ALLOWED_PROVENANCE_KINDS,
  ALLOWED_RELATION_TYPES,
  EntityFact,
  EvidenceFact,
  GraphDocument,
  RelationFact,
} from "../../domain/contracts.js";
import { GraphValidationError } from "../../domain/graph-validation-error.js";
import {
  GraphValidatorPort,
  ValidatedGraph,
} from "../../application/ports/graph-validator.port.js";

const MAX_ENTITIES = 10_000;
const MAX_RELATIONS = 50_000;
const MAX_EVIDENCE = 50_000;
const MAX_KEY_LENGTH = 255;
const MAX_SOURCE_LENGTH = 1024;
const MAX_EXCERPT_LENGTH = 4096;
const MAX_METADATA_BYTES = 64 * 1024;

export class GraphValidator implements GraphValidatorPort {
  public validateAndCanonicalize(document: unknown): ValidatedGraph {
    if (!document || typeof document !== "object") {
      throw new GraphValidationError("graph document must be an object");
    }

    const doc = document as Record<string, unknown>;
    if (doc.schema_version !== "1.0") {
      throw new GraphValidationError(
        `unsupported schema_version: expected '1.0', got '${doc.schema_version}'`
      );
    }

    if (!Array.isArray(doc.entities)) {
      throw new GraphValidationError("entities must be an array");
    }
    if (!Array.isArray(doc.relations)) {
      throw new GraphValidationError("relations must be an array");
    }
    if (!Array.isArray(doc.evidence)) {
      throw new GraphValidationError("evidence must be an array");
    }

    if (doc.entities.length > MAX_ENTITIES) {
      throw new GraphValidationError(`entity count exceeds limit of ${MAX_ENTITIES}`);
    }
    if (doc.relations.length > MAX_RELATIONS) {
      throw new GraphValidationError(`relation count exceeds limit of ${MAX_RELATIONS}`);
    }
    if (doc.evidence.length > MAX_EVIDENCE) {
      throw new GraphValidationError(`evidence count exceeds limit of ${MAX_EVIDENCE}`);
    }

    const entityKeys = new Set<string>();
    const validatedEntities: EntityFact[] = [];
    for (const ent of doc.entities) {
      const validated = this.validateEntity(ent);
      if (entityKeys.has(validated.key)) {
        throw new GraphValidationError(`duplicate entity key: '${validated.key}'`);
      }
      entityKeys.add(validated.key);
      validatedEntities.push(validated);
    }

    const relationRefs = new Set<string>();
    const validatedRelations: RelationFact[] = [];
    for (const rel of doc.relations) {
      const validated = this.validateRelation(rel, entityKeys);
      if (relationRefs.has(validated.ref)) {
        throw new GraphValidationError(`duplicate relation ref: '${validated.ref}'`);
      }
      relationRefs.add(validated.ref);
      validatedRelations.push(validated);
    }

    const validatedEvidence: EvidenceFact[] = [];
    for (const ev of doc.evidence) {
      const validated = this.validateEvidence(ev, relationRefs);
      validatedEvidence.push(validated);
    }

    // Canonical sorting
    // 1. Entities by key
    validatedEntities.sort((a, b) => a.key.localeCompare(b.key));

    // 2. Relations by ref, source_entity_key, type, then target_entity_key
    validatedRelations.sort((a, b) => {
      const refCmp = a.ref.localeCompare(b.ref);
      if (refCmp !== 0) return refCmp;
      const srcCmp = a.source_entity_key.localeCompare(b.source_entity_key);
      if (srcCmp !== 0) return srcCmp;
      const typeCmp = a.type.localeCompare(b.type);
      if (typeCmp !== 0) return typeCmp;
      return a.target_entity_key.localeCompare(b.target_entity_key);
    });

    // 3. Evidence by source, relation_ref, then canonical metadata JSON
    validatedEvidence.sort((a, b) => {
      const srcCmp = a.source.localeCompare(b.source);
      if (srcCmp !== 0) return srcCmp;
      const refA = a.relation_ref ?? "";
      const refB = b.relation_ref ?? "";
      const refCmp = refA.localeCompare(refB);
      if (refCmp !== 0) return refCmp;
      const metaA = this.canonicalizeJson(a.metadata ?? {});
      const metaB = this.canonicalizeJson(b.metadata ?? {});
      return metaA.localeCompare(metaB);
    });

    const canonicalDocument: GraphDocument = {
      schema_version: "1.0",
      entities: validatedEntities,
      relations: validatedRelations,
      evidence: validatedEvidence,
    };

    const canonicalJson = this.canonicalizeJson(canonicalDocument);
    const sha256 = createHash("sha256").update(canonicalJson, "utf8").digest("hex");

    return {
      document: canonicalDocument,
      canonicalJson,
      sha256,
      counts: {
        entities: validatedEntities.length,
        relations: validatedRelations.length,
        evidence: validatedEvidence.length,
      },
    };
  }

  private validateEntity(raw: unknown): EntityFact {
    if (!raw || typeof raw !== "object") {
      throw new GraphValidationError("entity must be an object");
    }
    const item = raw as Record<string, unknown>;
    if (!item.key || typeof item.key !== "string" || !item.key.trim()) {
      throw new GraphValidationError("entity key is required");
    }
    if (item.key.length > MAX_KEY_LENGTH) {
      throw new GraphValidationError(`entity key exceeds max length of ${MAX_KEY_LENGTH}`);
    }
    if (!item.type || typeof item.type !== "string" || !ALLOWED_ENTITY_TYPES.includes(item.type as any)) {
      throw new GraphValidationError(`invalid entity type: '${item.type}'`);
    }
    if (item.name !== undefined && typeof item.name !== "string") {
      throw new GraphValidationError("entity name must be a string if provided");
    }
    if (item.canonical_key !== undefined && typeof item.canonical_key !== "string") {
      throw new GraphValidationError("entity canonical_key must be a string if provided");
    }

    const metadata = this.validateMetadata(item.metadata);

    return {
      key: item.key.trim(),
      type: item.type as any,
      name: item.name as string | undefined,
      canonical_key: item.canonical_key as string | undefined,
      metadata,
    };
  }

  private validateRelation(raw: unknown, entityKeys: Set<string>): RelationFact {
    if (!raw || typeof raw !== "object") {
      throw new GraphValidationError("relation must be an object");
    }
    const item = raw as Record<string, unknown>;
    if (!item.ref || typeof item.ref !== "string" || !item.ref.trim()) {
      throw new GraphValidationError("relation ref is required");
    }
    if (item.ref.length > MAX_KEY_LENGTH) {
      throw new GraphValidationError(`relation ref exceeds max length of ${MAX_KEY_LENGTH}`);
    }
    if (!item.source_entity_key || typeof item.source_entity_key !== "string") {
      throw new GraphValidationError("relation source_entity_key is required");
    }
    if (!entityKeys.has(item.source_entity_key)) {
      throw new GraphValidationError(
        `dangling relation source endpoint: '${item.source_entity_key}' not found in entities`
      );
    }
    if (!item.target_entity_key || typeof item.target_entity_key !== "string") {
      throw new GraphValidationError("relation target_entity_key is required");
    }
    if (!entityKeys.has(item.target_entity_key)) {
      throw new GraphValidationError(
        `dangling relation target endpoint: '${item.target_entity_key}' not found in entities`
      );
    }
    if (!item.type || typeof item.type !== "string" || !ALLOWED_RELATION_TYPES.includes(item.type as any)) {
      throw new GraphValidationError(`invalid relation type: '${item.type}'`);
    }
    if (
      !item.provenance ||
      typeof item.provenance !== "string" ||
      !ALLOWED_PROVENANCE_KINDS.includes(item.provenance as any)
    ) {
      throw new GraphValidationError(`invalid provenance kind: '${item.provenance}'`);
    }

    const metadata = this.validateMetadata(item.metadata);

    return {
      ref: item.ref.trim(),
      source_entity_key: item.source_entity_key,
      type: item.type as any,
      target_entity_key: item.target_entity_key,
      provenance: item.provenance as any,
      metadata,
    };
  }

  private validateEvidence(raw: unknown, relationRefs: Set<string>): EvidenceFact {
    if (!raw || typeof raw !== "object") {
      throw new GraphValidationError("evidence must be an object");
    }
    const item = raw as Record<string, unknown>;
    if (!item.source || typeof item.source !== "string" || !item.source.trim()) {
      throw new GraphValidationError("evidence source is required");
    }
    if (item.source.length > MAX_SOURCE_LENGTH) {
      throw new GraphValidationError(`evidence source exceeds max length of ${MAX_SOURCE_LENGTH}`);
    }
    if (item.excerpt !== undefined) {
      if (typeof item.excerpt !== "string") {
        throw new GraphValidationError("evidence excerpt must be a string if provided");
      }
      if (item.excerpt.length > MAX_EXCERPT_LENGTH) {
        throw new GraphValidationError(`evidence excerpt exceeds max length of ${MAX_EXCERPT_LENGTH}`);
      }
    }
    if (item.relation_ref !== undefined && item.relation_ref !== null) {
      if (typeof item.relation_ref !== "string" || !item.relation_ref.trim()) {
        throw new GraphValidationError("evidence relation_ref must be non-empty string");
      }
      if (!relationRefs.has(item.relation_ref)) {
        throw new GraphValidationError(
          `dangling evidence relation_ref: '${item.relation_ref}' not found in relations`
        );
      }
    }

    const metadata = this.validateMetadata(item.metadata);

    return {
      source: item.source.trim(),
      excerpt: item.excerpt as string | undefined,
      relation_ref: (item.relation_ref as string) || undefined,
      metadata,
    };
  }

  private validateMetadata(raw: unknown): Record<string, unknown> | undefined {
    if (raw === undefined || raw === null) {
      return undefined;
    }
    if (typeof raw !== "object" || Array.isArray(raw)) {
      throw new GraphValidationError("metadata must be a JSON object");
    }
    const str = JSON.stringify(raw);
    if (Buffer.byteLength(str, "utf8") > MAX_METADATA_BYTES) {
      throw new GraphValidationError(`metadata object exceeds ${MAX_METADATA_BYTES} bytes`);
    }
    return raw as Record<string, unknown>;
  }

  private canonicalizeJson(obj: unknown): string {
    if (obj === null || typeof obj !== "object") {
      return JSON.stringify(obj);
    }
    if (Array.isArray(obj)) {
      return "[" + obj.map((item) => this.canonicalizeJson(item)).join(",") + "]";
    }
    const record = obj as Record<string, unknown>;
    const sortedKeys = Object.keys(record).sort();
    const parts = sortedKeys.map(
      (key) => `${JSON.stringify(key)}:${this.canonicalizeJson(record[key])}`
    );
    return "{" + parts.join(",") + "}";
  }
}
