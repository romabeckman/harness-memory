from uuid import NAMESPACE_DNS, UUID, uuid4, uuid5
import pytest
from core.infrastructure.postgres.models.tenant_id import TenantId
from core.infrastructure.postgres.models.tenant_uuid import TenantUUID


class TestTenantId:
    def test_bind_processor_accepts_valid_uuid(self):
        t_id = TenantId()
        proc = t_id.bind_processor(None)
        raw_uuid = uuid4()
        assert proc(raw_uuid) == raw_uuid

    def test_bind_processor_accepts_valid_uuid_string(self):
        t_id = TenantId()
        proc = t_id.bind_processor(None)
        raw_uuid = uuid4()
        assert proc(str(raw_uuid)) == raw_uuid

    def test_bind_processor_maps_valid_slug_to_uuid5(self):
        t_id = TenantId()
        proc = t_id.bind_processor(None)
        expected = uuid5(NAMESPACE_DNS, "tenant-a")
        assert proc("tenant-a") == expected

    def test_bind_processor_rejects_empty_and_blank(self):
        t_id = TenantId()
        proc = t_id.bind_processor(None)
        with pytest.raises(ValueError, match="must not be empty or blank"):
            proc("")
        with pytest.raises(ValueError, match="must not be empty or blank"):
            proc("   ")

    def test_bind_processor_rejects_invalid_slug(self):
        t_id = TenantId()
        proc = t_id.bind_processor(None)
        with pytest.raises(ValueError, match="Invalid UUID or slug format"):
            proc("invalid slug with spaces")
        with pytest.raises(ValueError, match="Invalid UUID or slug format"):
            proc("invalid!@#$%")

    def test_result_processor_wraps_in_tenant_uuid(self):
        t_id = TenantId()
        proc = t_id.result_processor(None, None)
        raw_uuid = uuid4()
        result = proc(raw_uuid)
        assert isinstance(result, TenantUUID)
        assert result == raw_uuid
