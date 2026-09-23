from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from api.adapters.http.knowledge_publication_routes import create_knowledge_publication_router
from core.domain.tenant_security.value_objects.authenticated_principal import AuthenticatedPrincipal


def test_baseline_uses_requested_tenant_for_scoped_publisher():
    execute = Mock(return_value={"graph": {"entities": []}})
    app = FastAPI()
    app.include_router(create_knowledge_publication_router(None,
        lambda: AuthenticatedPrincipal("pipeline", "trusted", frozenset({"memory:publish"})),
        SimpleNamespace(execute=execute)), prefix="/v1")
    target_tenant_id = str(uuid4())
    response = TestClient(app).get("/v1/knowledge-publications/latest",
        params={"project_key": "orders", "environment": "production", "tenant_id": target_tenant_id})
    assert response.status_code == 200
    execute.assert_called_once_with("orders", "production", target_tenant_id)


def test_scoped_publisher_baseline_searches_all_tenants_without_filter():
    execute = Mock(return_value={"graph": {"entities": []}})
    app = FastAPI()
    app.include_router(create_knowledge_publication_router(None,
        lambda: AuthenticatedPrincipal("pipeline", "trusted", frozenset({"memory:publish"})),
        SimpleNamespace(execute=execute)), prefix="/v1")
    response = TestClient(app).get("/v1/knowledge-publications/latest",
        params={"project_key": "orders", "environment": "production"})
    assert response.status_code == 200
    execute.assert_called_once_with("orders", "production", None)


def test_admin_baseline_reads_all_tenants_by_default():
    execute = Mock(return_value={"graph": {"entities": []}})
    admin = AuthenticatedPrincipal("admin", "*", frozenset({"memory:read"}), is_admin=True)
    app = FastAPI()
    app.include_router(create_knowledge_publication_router(None, lambda: admin,
        SimpleNamespace(execute=execute)), prefix="/v1")
    response = TestClient(app).get("/v1/knowledge-publications/latest",
        params={"project_key": "orders", "environment": "production"})

    assert response.status_code == 200
    execute.assert_called_once_with("orders", "production", None)


@pytest.mark.parametrize("status", [401, 403])
def test_baseline_requires_publisher_authentication(status):
    def denied():
        raise HTTPException(status_code=status)

    execute = Mock()
    app = FastAPI()
    app.include_router(create_knowledge_publication_router(None, denied,
        SimpleNamespace(execute=execute)), prefix="/v1")
    response = TestClient(app).get("/v1/knowledge-publications/latest",
        params={"project_key": "orders", "environment": "production"})
    assert response.status_code == status
    execute.assert_not_called()
