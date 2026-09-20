from __future__ import annotations

from collections.abc import AsyncIterator, Awaitable, Callable, Iterator
from contextlib import asynccontextmanager, contextmanager
from contextvars import ContextVar, Token
from inspect import isawaitable, iscoroutinefunction
from typing import TypeVar

from core.domain.tenant_security.value_objects.authenticated_principal import AuthenticatedPrincipal


T = TypeVar("T")


class RequestSecurityContext:
    """Immutable principal bound for one request and always reset on exit."""

    def __init__(self):
        self._principal: ContextVar[AuthenticatedPrincipal | None] = ContextVar(
            "authenticated_principal", default=None
        )

    def require(self) -> AuthenticatedPrincipal:
        principal = self._principal.get()
        if principal is None:
            raise RuntimeError("authenticated principal is required")
        return principal

    def current(self) -> AuthenticatedPrincipal | None:
        return self._principal.get()

    def bind(
        self,
        principal: AuthenticatedPrincipal,
        call_next: Callable[[], T | Awaitable[T]] | None = None,
    ):
        if call_next is None:
            return self._binding(principal)
        if iscoroutinefunction(call_next):
            async def _run_async_callable():
                token = self._principal.set(principal)
                try:
                    return await call_next()
                finally:
                    self._principal.reset(token)

            return _run_async_callable()
        token: Token = self._principal.set(principal)
        try:
            result = call_next()
        except BaseException:
            self._principal.reset(token)
            raise
        if isawaitable(result):
            async def _await_bound():
                try:
                    return await result
                finally:
                    self._principal.reset(token)

            return _await_bound()
        self._principal.reset(token)
        return result

    def run(self, principal: AuthenticatedPrincipal, call_next):
        return self.bind(principal, call_next)

    @contextmanager
    def _binding(self, principal: AuthenticatedPrincipal) -> Iterator[AuthenticatedPrincipal]:
        token: Token = self._principal.set(principal)
        try:
            yield principal
        finally:
            self._principal.reset(token)

    @asynccontextmanager
    async def bind_async(
        self, principal: AuthenticatedPrincipal
    ) -> AsyncIterator[AuthenticatedPrincipal]:
        with self._binding(principal):
            yield principal

    def clear(self) -> None:
        self._principal.set(None)
