from uuid import uuid4
import pytest
from api.application.services.project_management_service import ProjectManagementService


class DummyProjectRepo:
    def __init__(self):
        self.projects = []

    def create_project(self, tenant_id, key, name, metadata):
        p = {
            "id": str(uuid4()),
            "tenant_id": str(tenant_id),
            "key": key,
            "name": name,
            "metadata": metadata,
        }
        self.projects.append(p)
        return p

    def get_project(self, tenant_id, key):
        for p in self.projects:
            if p["tenant_id"] == str(tenant_id) and p["key"] == key:
                return p
        return None

    def list_projects(self, tenant_id=None, query=None, limit=100, offset=0):
        items = self.projects
        if tenant_id:
            items = [p for p in items if p["tenant_id"] == str(tenant_id)]
        if query:
            items = [
                p
                for p in items
                if query.lower() in (p["name"] or "").lower() or query.lower() in p["key"].lower()
            ]
        return {
            "items": items[offset : offset + limit],
            "total": len(items),
            "limit": limit,
            "offset": offset,
        }

    def update_project(self, tenant_id, key, values):
        p = self.get_project(tenant_id, key)
        if not p:
            return None
        p.update(values)
        return p

    def delete_project(self, tenant_id, key):
        p = self.get_project(tenant_id, key)
        if p:
            self.projects.remove(p)
            return True
        return False


def test_project_management_service_list_and_get():
    repo = DummyProjectRepo()
    service = ProjectManagementService(repo)
    t1 = uuid4()
    p1 = service.create(t1, "proj-1", "Project 1", {})

    res = service.list(tenant_id=t1, query=None, limit=10, offset=0)
    assert res["total"] == 1
    assert res["items"][0]["key"] == "proj-1"

    found = service.get(t1, "proj-1")
    assert found["key"] == "proj-1"

    with pytest.raises(LookupError):
        service.get(t1, "non-existent")
