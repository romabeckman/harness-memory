from collections.abc import Iterable
from contextvars import ContextVar

from core.application.snapshot_publication.errors.missing_tenant_context import MissingTenantContext
from core.application.snapshot_publication.types.publication_context import PublicationContext

from .authorization_failure import AuthorizationFailure


class TenantContextProvider:
    def __init__(
        self,
        tenant_id: str | None = None,
        scopes: Iterable[str] | None = None,
    ):
        normalized_scopes = None if scopes is None else frozenset(scopes)
        self._context: ContextVar[PublicationContext | None] = ContextVar(
            "publication_context",
            default=(PublicationContext(tenant_id, normalized_scopes) if tenant_id else None),
        )

    def require(self) -> PublicationContext:
        context = self._context.get()
        if context is None:
            raise MissingTenantContext("trusted tenant context is required")
        return context

    def set(self, tenant_id: str, scopes: Iterable[str] | None = None) -> None:
        normalized_scopes = None if scopes is None else frozenset(scopes)
        self._context.set(PublicationContext(tenant_id, normalized_scopes))

    def require_scope(self, scope: str) -> PublicationContext:
        context = self.require()
        if context.scopes is None or scope not in context.scopes:
            raise AuthorizationFailure("required MCP scope is missing")
        return context

    def clear(self) -> None:
        self._context.set(None)
