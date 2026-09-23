from collections.abc import Iterable
from contextvars import ContextVar

from core.application.snapshot_publication.errors.missing_tenant_context import MissingTenantContext
from core.application.snapshot_publication.types.publication_context import PublicationContext

from .authorization_failure import AuthorizationFailure
from .request_security_context import RequestSecurityContext


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
        self.security_context = RequestSecurityContext()

    def require(self) -> PublicationContext:
        context = self._context.get()
        if context is None:
            raise MissingTenantContext("trusted tenant context is required")
        return context

    def current_principal(self):
        return self.security_context.current()

    def set(self, tenant_id: str, scopes: Iterable[str] | None = None) -> None:
        normalized_scopes = None if scopes is None else frozenset(scopes)
        self._context.set(PublicationContext(tenant_id, normalized_scopes))

    def bind_principal(self, principal):
        """Bind principal and derived publication context for one request."""
        tenant_token = self._context.set(PublicationContext(
            principal.tenant_id, principal.scopes, principal.is_admin))
        principal_binding = self.security_context.bind(principal)

        class _Binding:
            def __enter__(_self):
                _self._principal_context = principal_binding.__enter__()
                return _self._principal_context

            def __exit__(_self, exc_type, exc, tb):
                try:
                    return principal_binding.__exit__(exc_type, exc, tb)
                finally:
                    self._context.reset(tenant_token)

        return _Binding()

    def require_scope(self, scope: str) -> PublicationContext:
        context = self.require()
        if (context.scopes is None and scope == "memory:impact") or (
            context.scopes is not None and scope not in context.scopes
        ):
            raise AuthorizationFailure("required MCP scope is missing", required_scope=scope)
        if scope == "memory:read" and self.current_principal() is not None:
            return PublicationContext(context.tenant_id, context.scopes, is_admin=True)
        return context

    def clear(self) -> None:
        self._context.set(None)

    def has_fixed_context(self) -> bool:
        return self._context.get() is not None and self.security_context.current() is None
