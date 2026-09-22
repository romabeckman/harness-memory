import { GraphDocument } from "../../domain/contracts.js";

export interface ValidatedGraph {
  document: GraphDocument;
  canonicalJson: string;
  sha256: string;
  counts: {
    entities: number;
    relations: number;
    evidence: number;
  };
}

export interface GraphValidatorPort {
  validateAndCanonicalize(document: unknown): ValidatedGraph;
}
