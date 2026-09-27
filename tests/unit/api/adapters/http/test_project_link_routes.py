from unittest.mock import Mock
from uuid import UUID, uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.adapters.http.project_link_routes import create_project_link_router
from core.domain.project_link.dtos.linked_project_summary import LinkedProjectSummary
from core.domain.project_link.entities.project_link import ProjectLink
from core.domain.project_link.value_objects.canonical_project_pair import CanonicalProjectPair


def _client():
    service = Mock()
    projects_service = Mock()
    router = create_project_link_router(service, projects_service)
    app = FastAPI()
    app.include_router(router, prefix="/v1")
    return TestClient(app), service, projects_service


def test_post_project_link_success():
    client, service, projects = _client()
    t1_id = uuid4()
    t2_id = uuid4()
    p1_id = uuid4()
    p2_id = uuid4()

    projects.get.side_effect = lambda tenant_id, key: {
        (t1_id, "alpha"): {
            "id": str(p1_id),
            "tenant_id": str(t1_id),
            "key": "alpha",
            "name": "Alpha",
        },
        (t2_id, "beta"): {"id": str(p2_id), "tenant_id": str(t2_id), "key": "beta", "name": "Beta"},
    }.get((tenant_id, key))

    created_link = ProjectLink(pair=CanonicalProjectPair(p1_id, p2_id))
    service.create_link.return_value = created_link

    response = client.post(
        f"/v1/projects/alpha/links?tenant_id={t1_id}",
        json={"target_project_key": "beta", "target_tenant_id": str(t2_id)},
    )

    assert response.status_code == 201
    data = response.json()
    assert data["id"] == str(created_link.id)
    assert data["linked_project"]["project_id"] == str(p2_id)
    assert data["linked_project"]["key"] == "beta"
    assert data["linked_project"]["name"] == "Beta"
    assert data["linked_project"]["tenant_id"] == str(t2_id)


def test_post_project_link_self_referential_422():
    client, service, projects = _client()
    t1_id = uuid4()
    service.create_link.side_effect = ValueError("cannot link project to itself")

    response = client.post(
        f"/v1/projects/alpha/links?tenant_id={t1_id}",
        json={"target_project_key": "alpha"},
    )

    assert response.status_code == 422
    assert "cannot link project to itself" in response.json()["detail"]


def test_post_project_link_not_found_404():
    client, service, projects = _client()
    t1_id = uuid4()
    service.create_link.side_effect = LookupError("project not found")

    response = client.post(
        f"/v1/projects/alpha/links?tenant_id={t1_id}",
        json={"target_project_key": "gamma"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "project not found"


def test_post_project_link_duplicate_409():
    client, service, projects = _client()
    t1_id = uuid4()
    service.create_link.side_effect = ValueError("project link already exists")

    response = client.post(
        f"/v1/projects/alpha/links?tenant_id={t1_id}",
        json={"target_project_key": "beta"},
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "project link already exists"


def test_get_project_links_success():
    client, service, _ = _client()
    t1_id = uuid4()
    p2_id = uuid4()
    service.list_links.return_value = [
        LinkedProjectSummary(project_id=p2_id, key="beta", name="Beta", tenant_id=t1_id)
    ]

    response = client.get(f"/v1/projects/alpha/links?tenant_id={t1_id}")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["project_id"] == str(p2_id)
    assert data[0]["key"] == "beta"


def test_get_project_links_project_not_found_404():
    client, service, _ = _client()
    t1_id = uuid4()
    service.list_links.side_effect = LookupError("project not found")

    response = client.get(f"/v1/projects/nonexistent/links?tenant_id={t1_id}")

    assert response.status_code == 404
    assert response.json()["detail"] == "project not found"


def test_delete_project_link_success():
    client, service, _ = _client()
    t1_id = uuid4()

    response = client.delete(f"/v1/projects/alpha/links/beta?tenant_id={t1_id}")

    assert response.status_code == 204
    service.delete_link.assert_called_once_with(t1_id, "alpha", "beta", None)


def test_delete_project_link_not_found_404():
    client, service, _ = _client()
    t1_id = uuid4()
    service.delete_link.side_effect = LookupError("project link not found")

    response = client.delete(f"/v1/projects/alpha/links/gamma?tenant_id={t1_id}")

    assert response.status_code == 404
    assert response.json()["detail"] == "project link not found"
