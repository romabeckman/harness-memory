from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from core.domain.platform.schema_incompatible_error import SchemaIncompatibleError
from core.infrastructure.postgres.alembic_runtime import AlembicRuntime
from core.infrastructure.postgres.schema_compatibility_checker import SchemaCompatibilityChecker

logger = logging.getLogger(__name__)


class ServerLifespanManager:
    """Coordinate schema verification, pool disposal, and telemetry shutdown."""

    def __init__(
        self,
        checker: SchemaCompatibilityChecker | None = None,
        alembic_runtime: AlembicRuntime | None = None,
        engine: Any | None = None,
        telemetry_tracer: Any | None = None,
    ):
        self._checker = checker or SchemaCompatibilityChecker()
        self._alembic_runtime = alembic_runtime
        self._engine = engine
        self._telemetry_tracer = telemetry_tracer

    def attach_engine(self, engine: Any) -> None:
        self._engine = engine

    def on_startup(self) -> None:
        if self._alembic_runtime is not None:
            try:
                status = self._checker.check(self._alembic_runtime)
            except Exception as error:
                safe_message = SchemaIncompatibleError._sanitize_message(str(error))
                logger.error("Database schema verification failed: %s", safe_message)
                raise RuntimeError(
                    f"database schema verification failed: {safe_message}"
                ) from error
            if not status.is_compatible():
                logger.error(
                    "Database schema incompatible: current '%s' does not match head '%s'",
                    status.current_revision,
                    status.head_revision,
                )
                raise SchemaIncompatibleError(status.current_revision, status.head_revision)
            logger.info("Database schema verified: revision '%s'", status.current_revision)

    def on_shutdown(self) -> None:
        if self._engine is not None and hasattr(self._engine, "dispose"):
            self._engine.dispose()
        if self._alembic_runtime is not None and hasattr(self._alembic_runtime, "dispose"):
            self._alembic_runtime.dispose()
        if self._telemetry_tracer is not None:
            for method_name in ("force_flush", "shutdown"):
                method = getattr(self._telemetry_tracer, method_name, None)
                if method is not None:
                    try:
                        method()
                    except Exception:
                        logger.debug("telemetry shutdown failed", exc_info=True)

    @asynccontextmanager
    async def lifespan(self, server: Any) -> AsyncIterator[dict[str, Any]]:
        try:
            self.on_startup()
            yield {}
        finally:
            self.on_shutdown()
