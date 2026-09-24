import base64
import hashlib
import json
from uuid import uuid4

import pytest

from core.application.entity_discovery.contracts.entity_search_criteria import (
    EntitySearchCriteria,
)
from core.application.entity_discovery.contracts.entity_search_item import EntitySearchItem
from core.application.entity_discovery.services.search_criteria_normalizer import (
    NormalizeEntitySearch,
)
from core.application.entity_discovery.services.search_cursor_codec import SearchCursorCodec
from core.application.entity_discovery.value_objects.filter_fingerprint import FilterFingerprint
from core.application.entity_discovery.value_objects.search_cursor import SearchCursor
from core.domain.snapshot_publication.types.entity_type import EntityType


def _item(key="payments-api"):
    return EntitySearchItem(
        entity_id=uuid4(),
        key=key,
        name="Payments API",
        type=EntityType.API,
        project_key="payments",
        project_name="Payments",
        snapshot_id=uuid4(),
        revision=2,
    )


def test_normalizer_trims_filters_preserves_exact_case_and_normalizes_name():
    criteria = NormalizeEntitySearch().execute(
        {"key": " Payments-API ", "name": " Payments ", "type": "api", "project": " P "}
    )

    assert criteria == EntitySearchCriteria(
        key="Payments-API", name="payments", type=EntityType.API, project="P"
    )


def test_filter_fingerprint_is_deterministic_and_excludes_scope_and_pagination():
    criteria = EntitySearchCriteria(
        key="payments", name="pay", type=EntityType.API, project="p", query="database"
    )
    same = EntitySearchCriteria(
        key="payments", name="pay", type=EntityType.API, project="p", query="database"
    )
    different = EntitySearchCriteria(
        key="payments", name="pay", type=EntityType.API, project="p", query="postgres"
    )

    assert FilterFingerprint.from_criteria(criteria) == FilterFingerprint.from_criteria(same)
    assert FilterFingerprint.from_criteria(criteria) != FilterFingerprint.from_criteria(different)
    assert len(FilterFingerprint.from_criteria(criteria).value) == 64


def test_cursor_round_trip_has_only_version_fingerprint_and_sort_tuple():
    criteria = EntitySearchCriteria(key="payments")
    item = _item()
    codec = SearchCursorCodec()
    token = codec.encode(criteria, item)
    cursor = codec.decode(token, criteria)
    payload = json.loads(base64.urlsafe_b64decode(token + "=" * (-len(token) % 4)))

    assert cursor == SearchCursor(
        version=1,
        filter_fingerprint=FilterFingerprint.from_criteria(criteria),
        last_key=item.key,
        last_id=item.entity_id,
    )
    assert set(payload) == {"version", "filter_fingerprint", "last_key", "last_id"}
    assert "tenant" not in token.lower()


def test_cursor_keeps_legacy_fingerprint_when_query_filter_is_absent():
    criteria = EntitySearchCriteria(key="payments")
    legacy_filters = {
        "key": "payments",
        "name": None,
        "type": None,
        "project": None,
    }
    fingerprint = hashlib.sha256(
        json.dumps(legacy_filters, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    payload = {
        "version": 1,
        "filter_fingerprint": fingerprint,
        "last_key": "payments-api",
        "last_id": str(uuid4()),
    }
    token = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")

    cursor = SearchCursorCodec().decode(token, criteria)

    assert cursor.last_key == "payments-api"


@pytest.mark.parametrize(
    "token",
    ["not-base64", base64.urlsafe_b64encode(b'{"version":2}').decode().rstrip("="), "!" * 1025],
)
def test_cursor_rejects_malformed_unknown_version_and_oversized_tokens(token):
    with pytest.raises(ValueError):
        SearchCursorCodec().decode(token, EntitySearchCriteria(key="payments"))


def test_cursor_rejects_invalid_uuid_and_filter_mismatch():
    criteria = EntitySearchCriteria(key="payments")
    payload = {
        "version": 1,
        "filter_fingerprint": FilterFingerprint.from_criteria(criteria).value,
        "last_key": "payments-api",
        "last_id": "invalid",
    }
    token = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")

    with pytest.raises(ValueError):
        SearchCursorCodec().decode(token, criteria)

    valid_token = SearchCursorCodec().encode(criteria, _item())
    with pytest.raises(ValueError, match="filter"):
        SearchCursorCodec().decode(valid_token, EntitySearchCriteria(key="other"))


def test_cursor_rejects_switching_between_current_and_past_snapshots():
    current = EntitySearchCriteria(query="payments")
    token = SearchCursorCodec().encode(current, _item())

    with pytest.raises(ValueError, match="filter"):
        SearchCursorCodec().decode(
            token, EntitySearchCriteria(query="payments", include_past_snapshots=True)
        )


@pytest.mark.parametrize("last_key", ["", "   ", " payments-api "])
def test_cursor_rejects_blank_or_untrimmed_last_key(last_key):
    with pytest.raises(ValueError):
        SearchCursor(
            version=1,
            filter_fingerprint="a" * 64,
            last_key=last_key,
            last_id=uuid4(),
        )
