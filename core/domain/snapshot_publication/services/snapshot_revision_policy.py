from ..errors.revision_conflict import RevisionConflict
from ..errors.stale_revision import StaleRevision
from ..types.revision_decision import RevisionDecision
from ..value_objects.current_snapshot_descriptor import CurrentSnapshotDescriptor


class SnapshotRevisionPolicy:
    def decide(
        self,
        current: CurrentSnapshotDescriptor | None,
        candidate: CurrentSnapshotDescriptor,
    ) -> RevisionDecision:
        if current is None:
            return RevisionDecision.ACTIVATE
        if candidate.revision.value == current.revision.value:
            if candidate.payload_hash == current.payload_hash:
                return RevisionDecision.ALREADY_PUBLISHED
            raise RevisionConflict("revision already contains different content")
        if candidate.revision.value < current.revision.value:
            raise StaleRevision("candidate revision is stale")
        return RevisionDecision.ACTIVATE

    execute = decide


DecideSnapshotRevision = SnapshotRevisionPolicy
