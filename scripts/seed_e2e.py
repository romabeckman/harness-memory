import hashlib
import os
import sys
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.infrastructure.postgres.models.tenant import Tenant
from core.infrastructure.postgres.models.api_service_account import ApiServiceAccount
from core.infrastructure.postgres.models.api_access_token import ApiAccessToken


DEFAULT_DB_URL = "postgresql+psycopg2://harness_memory:harness_memory@localhost:5432/harness_memory"


def seed_database():
    db_url = os.getenv("DATABASE_URL", DEFAULT_DB_URL)
    print(f"Connecting to database: {db_url}")
    engine = create_engine(db_url)

    with Session(engine) as session:
        # 1. Tenant
        tenant_key = "e2e-tenant"
        stmt = select(Tenant).where(Tenant.key == tenant_key)
        tenant = session.scalars(stmt).first()

        if not tenant:
            tenant = Tenant(
                id=uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"),
                key=tenant_key,
                name="E2E Test Organization",
                status="active",
                metadata_json={"environment": "test", "seeded_by": "seed_e2e.py"},
            )
            session.add(tenant)
            session.flush()
            print(f"Created Tenant: {tenant.name} ({tenant.id})")
        else:
            print(f"Found existing Tenant: {tenant.name} ({tenant.id})")

        # 2. Service Account
        sa_name = "e2e-automation-account"
        stmt = select(ApiServiceAccount).where(
            ApiServiceAccount.tenant_id == tenant.id,
            ApiServiceAccount.name == sa_name,
        )
        service_account = session.scalars(stmt).first()

        if not service_account:
            service_account = ApiServiceAccount(
                id=uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"),
                tenant_id=tenant.id,
                name=sa_name,
            )
            session.add(service_account)
            session.flush()
            print(f"Created Service Account: {service_account.name} ({service_account.id})")
        else:
            print(f"Found existing Service Account: {service_account.name} ({service_account.id})")

        # 3. Pre-existing Token for testing list and revocation
        token_name = "pre-existing-e2e-token"
        token_plaintext = "hm_e2e_preexisting_secret_12345"
        token_hash = hashlib.sha256(token_plaintext.encode("utf-8")).hexdigest()

        stmt = select(ApiAccessToken).where(ApiAccessToken.token_hash == token_hash)
        existing_token = session.scalars(stmt).first()

        if not existing_token:
            token = ApiAccessToken(
                id=uuid.UUID("cccccccc-cccc-cccc-cccc-cccccccccccc"),
                service_account_id=service_account.id,
                name=token_name,
                token_hash=token_hash,
                scopes=["memory:read"],
                expires_at=datetime.now(UTC) + timedelta(days=90),
            )
            session.add(token)
            session.flush()
            print(f"Created Pre-existing Token: {token.name} ({token.id})")
        else:
            print(f"Found existing Token: {existing_token.name} ({existing_token.id})")

        session.commit()
        print("\n[SEED SUCCESS] E2E Database seeds successfully provisioned!")


if __name__ == "__main__":
    seed_database()
