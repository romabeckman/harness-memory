from uuid import uuid4
import pytest

from core.domain.knowledge_publication.value_objects.publication_id import PublicationId


class TestPublicationId:
    def test_creates_publication_id_successfully(self) -> None:
        raw_uuid = uuid4()
        pub_id = PublicationId(raw_uuid)
        assert pub_id.value == raw_uuid

    def test_rejects_non_uuid(self) -> None:
        with pytest.raises(TypeError, match="publication_id must be a UUID"):
            PublicationId("not-a-uuid")  # type: ignore[arg-type]

    def test_generate_creates_random_id(self) -> None:
        pub_id1 = PublicationId.generate()
        pub_id2 = PublicationId.generate()
        assert pub_id1 != pub_id2
