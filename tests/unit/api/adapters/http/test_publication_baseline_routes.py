from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from api.adapters.http.knowledge_publication_routes import create_knowledge_publication_router
from core.domain.tenant_security.value_objects.authenticated_principal import AuthenticatedPrincipal


def test_baseline_uses_authenticated_tenant_not_header():
    execute = Mock(return_value={"graph": {"entities": []}})
    app = FastAPI()
    app.include_router(create_knowledge_publication_router(None,
        lambda: AuthenticatedPrincipal("pipeline", "trusted", frozenset({"memory:publish"})),
        SimpleNamespace(execute=execute)), prefix="/v1")
    response = TestClient(app).get("/v1/knowledge-publications/latest",
        params={"project_key": "orders", "environment": "production"},
        headers={"X-Tenant-ID": "foreign"})
    assert response.status_code == 200
    execute.assert_called_once_with("orders", "production", "trusted")


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
