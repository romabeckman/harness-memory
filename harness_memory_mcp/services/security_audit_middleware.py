from __future__ import annotations

import asyncio
import logging
from uuid import uuid4

from fastmcp.exceptions import InsufficientScopeError
from fastmcp.server.auth import AccessToken, TokenVerifier
from fastmcp.server.auth.auth import AuthContextMiddleware, BearerAuthBackend
from fastmcp.server.dependencies import get_access_token
from fastmcp.server.middleware import Middleware
from starlette.middleware import Middleware as StarletteMiddleware
from starlette.middleware.authentication import AuthenticationMiddleware

from core.application.tenant_security.use_cases.record_security_audit.handler import (
    RecordSecurityAuditHandler,
)
from core.application.tenant_security.use_cases.record_security_audit.inbound import (
    SecurityAuditCommand,
)
from core.domain.tenant_security.types.audit_event_type import AuditEventType
from core.domain.tenant_security.types.audit_outcome import AuditOutcome
from core.domain.tenant_security.types.audit_phase import AuditPhase

from .authenticated_principal_factory import AuthenticatedPrincipalFactory
from .component_scope_policy import ComponentScopePolicy
from .tenant_context import TenantContextProvider

logger = logging.getLogger(__name__)


class SecurityAuditMiddleware(Middleware):
    """Bind verified access tokens and enforce component policy for every MCP message."""

    def __init__(
        self,
        tenant_context: TenantContextProvider,
        principal_factory: AuthenticatedPrincipalFactory,
        policy: ComponentScopePolicy | None = None,
        audit_handler: RecordSecurityAuditHandler | None = None,
    ):
        self.tenant_context = tenant_context
        self.principal_factory = principal_factory
        self.policy = policy or ComponentScopePolicy()
        self.audit_handler = audit_handler

    async def __call__(self, context, call_next):
        token = get_access_token()
        if token is None:
            return await call_next(context)
        principal = self.principal_factory.from_verified_claims(token.claims)
        with self.tenant_context.bind_principal(principal):
            return await call_next(context)

    async def on_call_tool(self, context, call_next):
        return await self._run_typed(
            "tool", context.message.name, context, call_next
        )

    async def on_read_resource(self, context, call_next):
        return await self._run_typed(
            "resource", str(context.message.uri), context, call_next
        )

    async def on_get_prompt(self, context, call_next):
        return await self._run_typed(
            "prompt", context.message.name, context, call_next
        )

    async def _run_typed(self, kind, name, context, call_next):
        token = get_access_token()
        if token is None:
            return await call_next(context)
        principal = self.principal_factory.from_verified_claims(token.claims)
        with self.tenant_context.bind_principal(principal):
            # AuthMiddleware normally performs this check.  Repeat it here so
            # direct middleware composition and future transports cannot skip
            # authorization after the request principal is bound.
            if getattr(context, "method", None) or hasattr(context, "fastmcp_context"):
                if getattr(context, "method", None):
                    self._authorize_request(context, principal)
                else:
                    self._authorize_component(principal, kind, name)
            else:
                # Preserve compatibility with direct unit invocations that
                # provide only a component message.
                self._audit_component_denial(kind, name)
            return await call_next(context)

    def _authorize_request(self, context, principal) -> None:
        method = context.method
        params = context.message
        kind_name = None
        kind = None
        if method == "tools/call":
            kind, kind_name = "tool", getattr(params, "name", None)
        elif method == "resources/read":
            kind, kind_name = "resource", getattr(params, "uri", None)
        elif method == "prompts/get":
            kind, kind_name = "prompt", getattr(params, "name", None)
        if kind and kind_name:
            self._authorize_component(principal, kind, str(kind_name))

    def _authorize_component(self, principal, kind: str, name: str) -> None:
        required = self.policy.required_scope(kind, name)
        if required is None or required not in principal.scopes:
            self._record_failure(principal, kind, name, required)
            raise InsufficientScopeError(
                [required] if required else [],
                message=(
                    "Authorization failed: insufficient scope"
                    + (f" (required: {required})" if required else "")
                ),
            )

    def _record_failure(self, principal, kind: str, name: str, required: str | None):
        if self.audit_handler is None:
            return
        try:
            self.audit_handler.execute(
                SecurityAuditCommand(
                    request_id=uuid4(),
                    event_type=AuditEventType.AUTHORIZATION_FAILURE,
                    phase=AuditPhase.COMPLETED,
                    outcome=AuditOutcome.DENIED,
                    component_kind=kind,
                    component_name=name,
                    required_scope=required,
                    tenant_id=principal.tenant_id,
                    subject=principal.subject,
                    reason_code="insufficient_scope",
                )
            )
        except Exception:
            logger.error("security audit persistence failed for authorization denial")

    def _audit_component_denial(self, kind: str, name: str) -> None:
        principal = self._principal_or_none()
        if principal is None:
            return
        required = self.policy.required_scope(kind, name)
        if required is None or required not in principal.scopes:
            self._record_failure(principal, kind, name, required)

    async def on_list_tools(self, context, call_next):
        result = await call_next(context)
        principal = self._principal_or_none() or self._principal_from_token()
        if principal is None:
            return result
        return self.policy.filter_components(principal, "tool", result)

    async def on_list_resources(self, context, call_next):
        result = await call_next(context)
        principal = self._principal_or_none() or self._principal_from_token()
        return (
            result
            if principal is None
            else self.policy.filter_components(principal, "resource", result)
        )

    async def on_list_resource_templates(self, context, call_next):
        result = await call_next(context)
        principal = self._principal_or_none() or self._principal_from_token()
        return (
            result
            if principal is None
            else self.policy.filter_components(principal, "resource", result)
        )

    async def on_list_prompts(self, context, call_next):
        result = await call_next(context)
        principal = self._principal_or_none() or self._principal_from_token()
        return (
            result
            if principal is None
            else self.policy.filter_components(principal, "prompt", result)
        )

    def _principal_or_none(self):
        return self.tenant_context.security_context.current()

    def _principal_from_token(self):
        token = get_access_token()
        if token is None:
            return None
        try:
            return self.principal_factory.from_verified_claims(token.claims)
        except ValueError:
            return None


class AuditingTokenVerifier(TokenVerifier):
    """JWT verifier adapter that records denied authentication without token data."""

    def __init__(
        self,
        verifier: TokenVerifier,
        audit_handler: RecordSecurityAuditHandler | None = None,
        principal_factory: AuthenticatedPrincipalFactory | None = None,
    ):
        super().__init__(required_scopes=None)
        self.verifier = verifier
        self.audit_handler = audit_handler
        self.principal_factory = principal_factory
        self._audit_slots = asyncio.BoundedSemaphore(value=16)

    async def verify_token(self, token: str) -> AccessToken | None:
        try:
            access_token = await self.verifier.verify_token(token)
            if access_token is None:
                await self._audit_auth_failure_async()
                return None
            if self.principal_factory is not None:
                self.principal_factory.from_verified_claims(access_token.claims)
            return access_token
        except Exception:
            await self._audit_auth_failure_async()
            return None

    async def _audit_auth_failure_async(self) -> None:
        if self.audit_handler is None:
            return
        async with self._audit_slots:
            await asyncio.to_thread(self._audit_auth_failure)

    def _audit_auth_failure(self):
        if self.audit_handler is not None:
            try:
                self.audit_handler.execute(
                    SecurityAuditCommand(
                        request_id=uuid4(),
                        event_type=AuditEventType.AUTHENTICATION_FAILURE,
                        phase=AuditPhase.COMPLETED,
                        outcome=AuditOutcome.DENIED,
                        component_kind="http",
                        component_name="mcp",
                        reason_code="invalid_token",
                    )
                )
            except Exception:
                logger.error("security audit persistence failed for authentication denial")

    def get_middleware(self) -> list:
        return [
            StarletteMiddleware(
                AuthenticationMiddleware,
                backend=_AuditingBearerAuthBackend(self),
            ),
            StarletteMiddleware(AuthContextMiddleware),
        ]


class _AuditingBearerAuthBackend(BearerAuthBackend):
    def __init__(self, verifier: AuditingTokenVerifier):
        super().__init__(verifier)
        self._verifier = verifier

    async def authenticate(self, conn):
        header = next(
            (conn.headers.get(key) for key in conn.headers if key.lower() == "authorization"),
            None,
        )
        result = await super().authenticate(conn)
        if result is None and (not header or not header.lower().startswith("bearer ")):
            await self._verifier._audit_auth_failure_async()
        return result
