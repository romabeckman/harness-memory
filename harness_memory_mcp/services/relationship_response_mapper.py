import json

from pydantic import ValidationError

from core.application.relationship_context.errors.entity_context_ambiguous import (
    EntityContextAmbiguous,
)
from core.application.relationship_context.errors.entity_context_not_found import (
    EntityContextNotFound,
)
from core.application.relationship_context.errors.relationship_query_failure import (
    RelationshipQueryFailure,
)
from core.application.snapshot_publication.errors.missing_tenant_context import MissingTenantContext

from .authorization_failure import AuthorizationFailure


class RelationshipResponseMapper:
    MAX_RESPONSE_BYTES = 262144

    def success(self, result):
        payload = result.model_dump(mode="json") if hasattr(result, "model_dump") else result
        if not isinstance(payload, dict):
            return payload
        items = payload.get("items")
        if (
            isinstance(items, list)
            and items
            and isinstance(items[0], dict)
            and "entity" in items[0]
        ):
            return self._context_page(payload)
        return self._compact_context(payload, self.MAX_RESPONSE_BYTES)

    def _context_page(self, payload: dict) -> dict:
        if self._size(payload) <= self.MAX_RESPONSE_BYTES:
            return payload
        payload["response_truncated"] = True
        items = payload["items"]
        while len(items) > 1 and self._size(payload) > self.MAX_RESPONSE_BYTES:
            items.pop()
        if self._size(payload) > self.MAX_RESPONSE_BYTES:
            overhead = self._size({**payload, "items": []})
            items[0] = self._compact_context(items[0], self.MAX_RESPONSE_BYTES - overhead)
            if items[0].get("status") == "ERROR":
                return items[0]
        if self._size(payload) > self.MAX_RESPONSE_BYTES:
            return self._too_large()
        payload["count"] = len(items)
        payload["has_more"] = True
        return payload

    def _compact_context(self, payload: dict, max_bytes: int) -> dict:
        if self._size(payload) <= max_bytes:
            return payload
        payload["response_truncated"] = True
        for section in ("owners", "relations", "dependencies", "items"):
            for item in payload.get(section, []):
                for nested in (
                    item,
                    item.get("source", {}),
                    item.get("target", {}),
                    item.get("peer", {}),
                ):
                    if isinstance(nested, dict) and nested.get("metadata"):
                        nested["metadata"] = {}
        if self._size(payload) <= max_bytes:
            return payload
        for section in ("relations", "dependencies", "items"):
            for item in payload.get(section, []):
                if isinstance(item, dict) and item.get("evidence"):
                    item["evidence"] = []
        if self._size(payload) <= max_bytes:
            return payload
        for section in ("relations", "dependencies", "items", "owners"):
            rows = payload.get(section)
            while isinstance(rows, list) and rows and self._size(payload) > max_bytes:
                rows.pop()
                flag = f"{section}_truncated"
                if flag in payload:
                    payload[flag] = True
        if self._size(payload) <= max_bytes:
            return payload
        entity = payload.get("entity")
        if isinstance(entity, dict) and entity.get("metadata"):
            entity["metadata"] = {"truncated": True}
        if self._size(payload) <= max_bytes:
            return payload
        return self._too_large()

    @staticmethod
    def _too_large() -> dict:
        return {
            "status": "ERROR",
            "error": {
                "code": "RESPONSE_TOO_LARGE",
                "message": "context exceeds response byte limit",
            },
        }

    @staticmethod
    def _size(payload: dict) -> int:
        return len(json.dumps(payload, ensure_ascii=False).encode("utf-8"))

    def failure(self, error: Exception) -> dict:
        if isinstance(error, ValidationError):
            code, message = "INVALID_RELATIONSHIP_CONTRACT", "invalid relationship query contract"
        elif isinstance(error, MissingTenantContext):
            code, message = "MISSING_TENANT_CONTEXT", "trusted tenant context is required"
        elif isinstance(error, AuthorizationFailure):
            code, message = "RELATIONSHIP_UNAUTHORIZED", "relationship access is unauthorized"
        elif isinstance(error, EntityContextNotFound):
            code, message = "ENTITY_NOT_FOUND", "entity context not found"
        elif isinstance(error, EntityContextAmbiguous):
            code, message = "AMBIGUOUS_ENTITY", str(error)
        elif isinstance(error, RelationshipQueryFailure):
            code, message = "RELATIONSHIP_QUERY_FAILED", "relationship query failed"
        else:
            code, message = "RELATIONSHIP_QUERY_FAILED", "relationship query failed"
        return {"status": "ERROR", "error": {"code": code, "message": message}}
