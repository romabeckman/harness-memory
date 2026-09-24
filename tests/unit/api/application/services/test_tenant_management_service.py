from uuid import uuid4
import pytest
from api.application.services.tenant_management_service import TenantManagementService


class DummyRepo:
    def __init__(self):
        self.tenants = {}

    def create_tenant(self, key, name, metadata):
        t = {"id": str(uuid4()), "key": key, "name": name, "status": "active", "metadata": metadata}
        self.tenants[t["id"]] = t
        return t

    def get_tenant(self, tenant_id):
        return self.tenants.get(str(tenant_id))

    def update_tenant(self, tenant_id, values):
        t = self.tenants.get(str(tenant_id))
        if not t:
            return None
        t.update(values)
        return t

    def delete_tenant(self, tenant_id):
        if str(tenant_id) in self.tenants:
            del self.tenants[str(tenant_id)]
            return True
        return False

    def list_tenants(self, query=None, status=None, limit=100, offset=0):
        items = list(self.tenants.values())
        if status:
            items = [t for t in items if t["status"] == status]
        if query:
            items = [t for t in items if query.lower() in t["name"].lower() or query.lower() in t["key"].lower()]
        return {"items": items[offset : offset + limit], "total": len(items), "limit": limit, "offset": offset}


def test_tenant_management_service_list_and_get():
    repo = DummyRepo()
    service = TenantManagementService(repo)
    t1 = repo.create_tenant("t1", "Tenant One", {})
    t2 = repo.create_tenant("t2", "Tenant Two", {})
    repo.update_tenant(t2["id"], {"status": "disabled"})

    res = service.list(query=None, status="active", limit=10, offset=0)
    assert res["total"] == 1
    assert res["items"][0]["key"] == "t1"

    found = service.get(t1["id"])
    assert found["key"] == "t1"

    with pytest.raises(LookupError):
        service.get(uuid4())
