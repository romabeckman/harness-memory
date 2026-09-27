import re
from typing import Any
from uuid import NAMESPACE_DNS, UUID, uuid5

from sqlalchemy import Uuid
from sqlalchemy.engine import Dialect

from .tenant_uuid import TenantUUID

_SLUG_REGEX = re.compile(r"^[a-zA-Z0-9_-]+$")


class TenantId(Uuid):
    """Platform-wide Tenant ID type that safely handles UUID objects and legacy tenant slugs."""

    def __init__(self, as_uuid: bool = True, native_uuid: bool = True) -> None:
        super().__init__(as_uuid=as_uuid, native_uuid=native_uuid)

    def bind_processor(self, dialect: Dialect):
        parent_proc = super().bind_processor(dialect) if dialect is not None else None

        def process(value: Any) -> Any:
            if value is None:
                return None

            if isinstance(value, str):
                trimmed = value.strip()
                if not trimmed:
                    raise ValueError("tenant_id must not be empty or blank")
                try:
                    uuid_val = UUID(trimmed)
                except ValueError:
                    if _SLUG_REGEX.match(trimmed):
                        uuid_val = uuid5(NAMESPACE_DNS, trimmed)
                    else:
                        raise ValueError(f"Invalid UUID or slug format for tenant_id: '{value}'")
                value = uuid_val

            if not isinstance(value, UUID):
                raise ValueError(f"Invalid type for tenant_id: {type(value).__name__}")

            if parent_proc:
                return parent_proc(value)
            return value

        return process

    def result_processor(self, dialect: Dialect, coltype: Any):
        parent_proc = super().result_processor(dialect, coltype) if dialect is not None else None

        def process(value: Any) -> Any:
            if value is None:
                return None
            if parent_proc:
                res = parent_proc(value)
            elif isinstance(value, str):
                res = UUID(value)
            else:
                res = value

            if isinstance(res, UUID) and not isinstance(res, TenantUUID):
                return TenantUUID(res.hex)
            return res

        return process
