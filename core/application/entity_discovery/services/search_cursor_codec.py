import base64
import binascii
import json
import re

from core.application.entity_discovery.contracts.entity_search_criteria import (
    EntitySearchCriteria,
)
from core.application.entity_discovery.contracts.entity_search_item import EntitySearchItem
from core.application.entity_discovery.errors.cursor_validation import SearchCursorValidationError
from core.application.entity_discovery.value_objects.filter_fingerprint import FilterFingerprint
from core.application.entity_discovery.value_objects.search_cursor import SearchCursor


class SearchCursorCodec:
    MAX_LENGTH = 1024

    def encode(self, criteria: EntitySearchCriteria, item: EntitySearchItem) -> str:
        payload = {
            "filter_fingerprint": FilterFingerprint.from_criteria(criteria).value,
            "last_id": str(item.entity_id),
            "last_key": item.key,
            "version": 1,
        }
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")

    def decode(self, token: str, criteria: EntitySearchCriteria) -> SearchCursor:
        if not isinstance(token, str) or not 1 <= len(token) <= self.MAX_LENGTH:
            raise SearchCursorValidationError("invalid search cursor")
        if not re.fullmatch(r"[A-Za-z0-9_-]+", token):
            raise SearchCursorValidationError("invalid search cursor encoding")
        padded = token + "=" * (-len(token) % 4)
        try:
            raw = base64.b64decode(padded, altchars=b"-_", validate=True)
            payload = json.loads(raw.decode("utf-8"))
        except (binascii.Error, UnicodeDecodeError, json.JSONDecodeError, ValueError) as error:
            raise SearchCursorValidationError("invalid search cursor") from error
        if not isinstance(payload, dict) or set(payload) != {
            "version", "filter_fingerprint", "last_key", "last_id"
        }:
            raise SearchCursorValidationError("invalid search cursor payload")
        if payload.get("version") != 1 or isinstance(payload.get("version"), bool):
            raise SearchCursorValidationError("unsupported search cursor version")
        try:
            cursor = SearchCursor(
                version=payload["version"],
                filter_fingerprint=payload["filter_fingerprint"],
                last_key=payload["last_key"],
                last_id=payload["last_id"],
            )
        except (TypeError, ValueError) as error:
            raise SearchCursorValidationError("invalid search cursor payload") from error
        expected = FilterFingerprint.from_criteria(criteria)
        if cursor.filter_fingerprint != expected:
            raise SearchCursorValidationError("search cursor filter mismatch")
        return cursor
