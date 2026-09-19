import hashlib
from typing import Any

from core.domain.snapshot_publication.value_objects.payload_hash import PayloadHash

from .canonical_payload_serializer import CanonicalPayloadSerializer


class PayloadHashCalculator:
    def __init__(self, serializer: CanonicalPayloadSerializer | None = None):
        self._serializer = serializer or CanonicalPayloadSerializer()

    def calculate(self, payload: Any, tenant_id: str | None = None) -> PayloadHash:
        del tenant_id
        digest = hashlib.sha256(self._serializer.serialize(payload)).hexdigest()
        return PayloadHash(digest)

    execute = calculate


CalculatePayloadHash = PayloadHashCalculator
