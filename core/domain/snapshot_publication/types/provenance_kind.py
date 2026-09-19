from enum import Enum


class ProvenanceKind(str, Enum):
    DECLARED = "declared"
    INFERRED = "inferred"
    OBSERVED = "observed"
    MANUAL = "manual"
