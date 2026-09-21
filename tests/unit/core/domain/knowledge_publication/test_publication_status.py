from core.domain.knowledge_publication.types.publication_status import PublicationStatus


class TestPublicationStatus:
    def test_supports_expected_statuses(self) -> None:
        assert PublicationStatus.PENDING.value == "PENDING"
        assert PublicationStatus.COMPLETED.value == "COMPLETED"
        assert PublicationStatus.ALREADY_PUBLISHED.value == "ALREADY_PUBLISHED"
