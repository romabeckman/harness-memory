from uuid import uuid4

import pytest
from pydantic import ValidationError

from api.adapters.http.schemas.token_create import TokenCreate


@pytest.mark.parametrize("projects", [[], None])
@pytest.mark.parametrize("tenant", ["", None])
def test_accepts_empty_global_scope(projects, tenant):
    payload = TokenCreate.model_validate({
        "name": "global", "service_account_id": str(uuid4()),
        "project_keys": projects, "tenant_id": tenant,
    })
    assert not payload.project_keys


def test_rejects_blank_project_keys():
    with pytest.raises(ValidationError):
        TokenCreate(name="invalid", service_account_id=uuid4(), project_keys=[" "])
