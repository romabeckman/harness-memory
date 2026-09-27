import pytest
from uuid import UUID

from core.domain.project_link.value_objects.canonical_project_pair import CanonicalProjectPair


def test_create_canonical_project_pair_ordered():
    uuid_low = UUID("00000000-0000-0000-0000-000000000001")
    uuid_high = UUID("00000000-0000-0000-0000-000000000002")

    pair = CanonicalProjectPair(uuid_low, uuid_high)

    assert pair.project_a_id == uuid_low
    assert pair.project_b_id == uuid_high


def test_create_canonical_project_pair_reverse_order_normalized():
    uuid_low = UUID("00000000-0000-0000-0000-000000000001")
    uuid_high = UUID("00000000-0000-0000-0000-000000000002")

    pair = CanonicalProjectPair(uuid_high, uuid_low)

    assert pair.project_a_id == uuid_low
    assert pair.project_b_id == uuid_high


def test_reject_self_referential_pair():
    uuid_x = UUID("00000000-0000-0000-0000-000000000001")

    with pytest.raises(
        ValueError, match="cannot link project to itself|self-referential linking is prohibited"
    ):
        CanonicalProjectPair(uuid_x, uuid_x)


def test_equality_and_hash_symmetric():
    uuid_a = UUID("00000000-0000-0000-0000-000000000001")
    uuid_b = UUID("00000000-0000-0000-0000-000000000002")

    pair_1 = CanonicalProjectPair(uuid_a, uuid_b)
    pair_2 = CanonicalProjectPair(uuid_b, uuid_a)

    assert pair_1 == pair_2
    assert hash(pair_1) == hash(pair_2)


def test_inequality_different_projects():
    uuid_a = UUID("00000000-0000-0000-0000-000000000001")
    uuid_b = UUID("00000000-0000-0000-0000-000000000002")
    uuid_c = UUID("00000000-0000-0000-0000-000000000003")

    pair_1 = CanonicalProjectPair(uuid_a, uuid_b)
    pair_2 = CanonicalProjectPair(uuid_a, uuid_c)

    assert pair_1 != pair_2
