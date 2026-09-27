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
    def test_add_does_not_create_tenant_or_project(self):
        engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        Base.metadata.create_all(engine, tables=[Tenant.__table__, ApiUser.__table__])
        session_factory = sessionmaker(bind=engine, expire_on_commit=False)
        user = User(uuid4(), "Alice", "alice@example.com")

        ApiUserRepository(session_factory).add(user)

        with session_factory() as session:
            assert session.query(Tenant).count() == 0
            assert session.get(ApiUser, user.id).tenant_id is None

    def test_list_filters_and_pages_in_database(self):
        engine = create_engine(
            "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
        )
        Base.metadata.create_all(engine, tables=[Tenant.__table__, ApiUser.__table__])
        session_factory = sessionmaker(bind=engine, expire_on_commit=False)
        repo = ApiUserRepository(session_factory)
        for index in range(25):
            repo.add(User(uuid4(), f"Member {index}", f"member{index:02d}@example.com"))

        statements = []
        from sqlalchemy import event

        @event.listens_for(engine, "before_cursor_execute")
        def record_query(connection, cursor, statement, parameters, context, executemany):
            if statement.lstrip().upper().startswith("SELECT") and "FROM users" in statement:
                statements.append(statement.upper())

        result = repo.list(q="MEMBER", limit=5, offset=20)
        assert [user.email for user in result] == [f"member{index:02d}@example.com" for index in range(20, 25)]
        assert len(statements) == 1
        assert "LIMIT" in statements[0] and "OFFSET" in statements[0] and "LIKE" in statements[0]

    def test_add_preserves_explicit_tenant_binding(self):
        engine = create_engine(
            "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
        )
        Base.metadata.create_all(engine, tables=[Tenant.__table__, ApiUser.__table__])
        session_factory = sessionmaker(bind=engine, expire_on_commit=False)
        repo = ApiUserRepository(session_factory)

        user_id = uuid4()
        with session_factory() as session:
            session.add(Tenant(id=user_id, key=f"user-{user_id}", name="Existing", status="active"))
            session.commit()
        user = User(id=uuid4(), name="Alice", email="alice@example.com", tenant_id=user_id)
        repo.add(user)

        with session_factory() as session:
            assert session.get(ApiUser, user.id).tenant_id == user_id
            assert session.query(Tenant).count() == 1

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



