from dataclasses import dataclass

ADMIN_TENANT_ID = "*"


@dataclass(frozen=True, slots=True)
class AuthenticatedPrincipal:
    subject: str
    tenant_id: str
    scopes: frozenset[str]
    is_admin: bool = False

    def __post_init__(self) -> None:
        subject = self.subject.strip() if isinstance(self.subject, str) else ""
        tenant_id = self.tenant_id.strip() if isinstance(self.tenant_id, str) else ""
        if not subject:
            raise ValueError("subject is required")
        if len(subject) > 255:
            raise ValueError("subject exceeds 255 characters")
        if not tenant_id:
            raise ValueError("tenant identity is required")
        if len(tenant_id) > 255:
            raise ValueError("tenant identity exceeds 255 characters")
        if tenant_id == ADMIN_TENANT_ID and not self.is_admin:
            raise ValueError("global tenant identity requires an administrator principal")
        object.__setattr__(self, "subject", subject)
        object.__setattr__(self, "tenant_id", tenant_id)
        object.__setattr__(
            self,
            "scopes",
            frozenset(
                scope.strip()
                for scope in self.scopes
                if isinstance(scope, str) and scope.strip()
            ),
        )

    def has_scope(self, scope: str) -> bool:
        return scope in self.scopes
