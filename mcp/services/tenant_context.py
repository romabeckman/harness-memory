from contextvars import ContextVar

from core.application.snapshot_publication.errors.missing_tenant_context import MissingTenantContext
from core.application.snapshot_publication.types.publication_context import PublicationContext


class TenantContextProvider:
    def __init__(self, tenant_id: str | None = None):
        self._context: ContextVar[PublicationContext | None] = ContextVar(
            "publication_context", default=PublicationContext(tenant_id) if tenant_id else None
        )

    def require(self) -> PublicationContext:
        context = self._context.get()
        if context is None:
            raise MissingTenantContext("trusted tenant context is required")
        return context

    def set(self, tenant_id: str) -> None:
        self._context.set(PublicationContext(tenant_id))

    def clear(self) -> None:
        self._context.set(None)
