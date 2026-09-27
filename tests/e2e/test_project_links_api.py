from hashlib import sha256
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from api.server.app import create_app
from core.infrastructure.postgres.models import ApiAccessToken, ApiUser, Base, Project, Tenant


def _setup_app():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    admin_token = "admin-secret-token"
    app = create_app(session_factory, admin_token=admin_token)
    client = TestClient(app)
    return client, session_factory, admin_token


def _seed_tenants_and_projects(session_factory):
    with session_factory() as session, session.begin():
        t1 = Tenant(id=uuid4(), key="tenant-1", name="Tenant 1", status="active", metadata_json={})
        t2 = Tenant(id=uuid4(), key="tenant-2", name="Tenant 2", status="active", metadata_json={})
        session.add_all([t1, t2])
        session.flush()

        p_alpha = Project(id=uuid4(), tenant_id=t1.id, key="alpha", name="Project Alpha")
        p_beta = Project(id=uuid4(), tenant_id=t2.id, key="beta", name="Project Beta")
        session.add_all([p_alpha, p_beta])
        session.flush()

        # Seed reader user & token
        user = ApiUser(id=uuid4(), tenant_id=t1.id, name="Reader User", email="reader@test.com")
        session.add(user)
        session.flush()

        reader_hash = sha256(b"reader-secret-token").hexdigest()
        token = ApiAccessToken(
            id=uuid4(),
            user_id=user.id,
            name="Reader Token",
            token_hash=reader_hash,
            scopes=["memory:read"],
            allowed_projects=[],
        )
        session.add(token)
        session.flush()

        return t1.id, t2.id, p_alpha.id, p_beta.id


def test_create_and_list_links_bidirectionally_happy_path():
    client, session_factory, admin_token = _setup_app()
    t1_id, t2_id, p_alpha_id, p_beta_id = _seed_tenants_and_projects(session_factory)

    headers = {"Authorization": f"Bearer {admin_token}"}

    # 1. Create link from alpha to beta
    post_resp = client.post(
        f"/v1/projects/alpha/links?tenant_id={t1_id}",
        json={"target_project_key": "beta", "target_tenant_id": str(t2_id)},
        headers=headers,
    )
    assert post_resp.status_code == 201
    post_data = post_resp.json()
    assert post_data["linked_project"]["project_id"] == str(p_beta_id)
    assert post_data["linked_project"]["key"] == "beta"
    assert post_data["linked_project"]["tenant_id"] == str(t2_id)

    # 2. List links from alpha
    get_alpha = client.get(
        f"/v1/projects/alpha/links?tenant_id={t1_id}",
        headers=headers,
    )
    assert get_alpha.status_code == 200
    alpha_links = get_alpha.json()
    assert len(alpha_links) == 1
    assert alpha_links[0]["key"] == "beta"
    assert alpha_links[0]["tenant_id"] == str(t2_id)

    # 3. List links from beta (bidirectional resolution)
    get_beta = client.get(
        f"/v1/projects/beta/links?tenant_id={t2_id}",
        headers=headers,
    )
    assert get_beta.status_code == 200
    beta_links = get_beta.json()
    assert len(beta_links) == 1
    assert beta_links[0]["key"] == "alpha"
    assert beta_links[0]["tenant_id"] == str(t1_id)

    # 4. Delete link
    del_resp = client.delete(
        f"/v1/projects/alpha/links/beta?tenant_id={t1_id}&target_tenant_id={t2_id}",
        headers=headers,
    )
    assert del_resp.status_code == 204

    # 5. Verify disappearance from both sides
    assert client.get(f"/v1/projects/alpha/links?tenant_id={t1_id}", headers=headers).json() == []
    assert client.get(f"/v1/projects/beta/links?tenant_id={t2_id}", headers=headers).json() == []


def test_error_flows():
    client, session_factory, admin_token = _setup_app()
    t1_id, t2_id, _, _ = _seed_tenants_and_projects(session_factory)
    headers = {"Authorization": f"Bearer {admin_token}"}

    # 422 on self-link
    self_link_resp = client.post(
        f"/v1/projects/alpha/links?tenant_id={t1_id}",
        json={"target_project_key": "alpha"},
        headers=headers,
    )
    assert self_link_resp.status_code == 422

    # 404 on non-existent target project
    not_found_resp = client.post(
        f"/v1/projects/alpha/links?tenant_id={t1_id}",
        json={"target_project_key": "gamma"},
        headers=headers,
    )
    assert not_found_resp.status_code == 404

    # Create valid link
    client.post(
        f"/v1/projects/alpha/links?tenant_id={t1_id}",
        json={"target_project_key": "beta", "target_tenant_id": str(t2_id)},
        headers=headers,
    )

    # 409 on duplicate link creation (reverse order)
    dup_resp = client.post(
        f"/v1/projects/beta/links?tenant_id={t2_id}",
        json={"target_project_key": "alpha", "target_tenant_id": str(t1_id)},
        headers=headers,
    )
    assert dup_resp.status_code == 409

    # 404 on deleting non-existent link
    del_404 = client.delete(
        f"/v1/projects/alpha/links/gamma?tenant_id={t1_id}",
        headers=headers,
    )
    assert del_404.status_code == 404


def test_security_authorization():
    client, session_factory, _ = _setup_app()
    t1_id, _, _, _ = _seed_tenants_and_projects(session_factory)

    # 401 Unauthorized without header
    unauth_resp = client.post(
        f"/v1/projects/alpha/links?tenant_id={t1_id}",
        json={"target_project_key": "beta"},
    )
    assert unauth_resp.status_code == 401

    # 403 Forbidden with non-admin token
    reader_headers = {"Authorization": "Bearer reader-secret-token"}
    forbidden_resp = client.post(
        f"/v1/projects/alpha/links?tenant_id={t1_id}",
        json={"target_project_key": "beta"},
        headers=reader_headers,
    )
    assert forbidden_resp.status_code == 403
