from uuid import NAMESPACE_DNS, UUID, uuid4, uuid5
from core.infrastructure.postgres.models.tenant_uuid import TenantUUID


class TestTenantUUID:
    def test_equals_uuid_object(self):
        raw = uuid4()
        tenant_uuid = TenantUUID(raw.hex)
        assert tenant_uuid == raw
        assert raw == tenant_uuid

    def test_equals_valid_uuid_string(self):
        raw = uuid4()
        tenant_uuid = TenantUUID(raw.hex)
        assert tenant_uuid == str(raw)
        assert str(raw) == tenant_uuid

    def test_equals_legacy_slug_mapped(self):
        slug = "tenant-a"
        expected = uuid5(NAMESPACE_DNS, slug)
        tenant_uuid = TenantUUID(expected.hex)
        assert tenant_uuid == slug
        assert slug == tenant_uuid

    def test_not_equals_empty_blank_or_invalid(self):
        tenant_uuid = TenantUUID(uuid4().hex)
        assert tenant_uuid != ""
        assert tenant_uuid != "   "
        assert tenant_uuid != "invalid!@#$"
        assert tenant_uuid != 12345
        assert tenant_uuid is not None
