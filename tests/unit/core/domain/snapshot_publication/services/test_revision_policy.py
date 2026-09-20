from uuid import uuid4

import pytest

from core.domain.snapshot_publication.errors.revision_conflict import RevisionConflict
from core.domain.snapshot_publication.errors.stale_revision import StaleRevision
from core.domain.snapshot_publication.services.snapshot_revision_policy import (
    RevisionDecision,
    SnapshotRevisionPolicy,
)
from core.domain.snapshot_publication.value_objects.current_snapshot_descriptor import (
    CurrentSnapshotDescriptor,
)
from core.domain.snapshot_publication.value_objects.payload_hash import PayloadHash
from core.domain.snapshot_publication.value_objects.revision import Revision


def descriptor(revision, digest="a" * 64):
    return CurrentSnapshotDescriptor(uuid4(), Revision(revision), PayloadHash(digest))


def test_revision_policy_handles_activation_idempotency_conflict_and_staleness():
    policy = SnapshotRevisionPolicy()

    assert policy.decide(None, descriptor(1)) is RevisionDecision.ACTIVATE
    assert policy.decide(descriptor(2), descriptor(2)) is RevisionDecision.ALREADY_PUBLISHED
    with pytest.raises(RevisionConflict):
        policy.decide(descriptor(2), descriptor(2, "b" * 64))
    with pytest.raises(StaleRevision):
        policy.decide(descriptor(5), descriptor(3))
    assert policy.decide(descriptor(2), descriptor(5)) is RevisionDecision.ACTIVATE
