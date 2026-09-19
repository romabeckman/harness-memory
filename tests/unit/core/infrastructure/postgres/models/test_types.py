from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from core.infrastructure.postgres.models.foundation_id import FoundationId
from core.infrastructure.postgres.models.metadata import MetadataObject


def test_metadata_object_rejects_non_object_roots():
    for value in ([], "value", 1, None):
        with pytest.raises(ValidationError):
            MetadataObject(value=value)


def test_foundation_id_preserves_value_equality_and_immutability():
    identifier = uuid4()
    first = FoundationId(value=identifier)
    second = FoundationId(value=UUID(str(identifier)))

    assert first == second
    with pytest.raises(ValidationError):
        first.value = uuid4()


def test_foundation_id_distinguishes_different_values():
    assert FoundationId(value=uuid4()) != FoundationId(value=uuid4())
