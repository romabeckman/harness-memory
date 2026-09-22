from uuid import uuid4
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from api.domain.entities.user import User
from core.infrastructure.postgres.models.base import Base
from core.infrastructure.postgres.models.tenant import Tenant
from core.infrastructure.postgres.models.api_user import ApiUser
from core.infrastructure.postgres.repositories.api_user_repository import ApiUserRepository


class TestApiUserRepository:
    def test_add_provisions_tenant_with_full_uuid_key(self):
        engine = create_engine(
            "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
        )
        Base.metadata.create_all(engine, tables=[Tenant.__table__, ApiUser.__table__])
        session_factory = sessionmaker(bind=engine, expire_on_commit=False)
        repo = ApiUserRepository(session_factory)

        user_id = uuid4()
        user = User(id=user_id, name="Alice", email="alice@example.com")
        repo.add(user)

        with session_factory() as session:
            tenant = session.get(Tenant, user_id)
            assert tenant is not None
            assert tenant.key == f"user-{user_id}"
            assert tenant.name == "User Alice Tenant"
            assert tenant.status == "active"

    def test_add_concurrent_tenant_collision_recovers_via_savepoint(self):
        engine = create_engine(
            "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
        )
        Base.metadata.create_all(engine, tables=[Tenant.__table__, ApiUser.__table__])
        session_factory = sessionmaker(bind=engine, expire_on_commit=False)
        repo = ApiUserRepository(session_factory)

        user_id = uuid4()
        # Pre-seed the tenant to simulate concurrent provisioning
        with session_factory() as session:
            session.add(
                Tenant(
                    id=user_id,
                    key=f"user-{user_id}",
                    name="Pre-existing Tenant",
                    status="active",
                )
            )
            session.commit()

        user = User(id=user_id, name="Bob", email="bob@example.com")
        # Should not raise PendingRollbackError or crash
        saved = repo.add(user)
        assert saved.id == user_id

        with session_factory() as session:
            assert session.get(ApiUser, user_id) is not None

    def test_add_flush_integrity_error_rolls_back_savepoint_without_poisoning_session(
        self, monkeypatch
    ):
        engine = create_engine(
            "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
        )
        Base.metadata.create_all(engine, tables=[Tenant.__table__, ApiUser.__table__])
        session_factory = sessionmaker(bind=engine, expire_on_commit=False)
        repo = ApiUserRepository(session_factory)

        user_id = uuid4()
        user = User(id=user_id, name="Charlie", email="charlie@example.com")

        with session_factory() as session:
            session.add(
                Tenant(
                    id=user_id,
                    key=f"user-{user_id}",
                    name="Existing",
                    status="active",
                )
            )
            session.commit()

        def failing_ensure(session, t_id, name):
            from sqlalchemy.exc import IntegrityError
            try:
                with session.begin_nested():
                    raise IntegrityError("simulated duplicate key", params=None, orig=Exception())
            except IntegrityError:
                pass

        monkeypatch.setattr(repo, "_ensure_tenant", failing_ensure)

        saved = repo.add(user)
        assert saved.id == user_id

        with session_factory() as session:
            assert session.get(ApiUser, user_id) is not None


