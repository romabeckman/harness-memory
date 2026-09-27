from dataclasses import dataclass
from uuid import UUID

from .filter_fingerprint import FilterFingerprint


@dataclass(frozen=True, slots=True)
class SearchCursor:
    version: int
    filter_fingerprint: FilterFingerprint | str
    last_key: str
    last_id: UUID
    scope_hash: str | None = None
    context_hash: str | None = None
    pinned_snapshot_id: UUID | None = None

    def __post_init__(self) -> None:
        if self.version not in (1, 2) or isinstance(self.version, bool):
            raise ValueError("unsupported search cursor version")
        if self.version == 2:
            for field in ("scope_hash", "context_hash"):
                value = getattr(self, field)
                if (
                    not isinstance(value, str)
                    or len(value) != 64
                    or any(c not in "0123456789abcdef" for c in value)
                ):
                    raise ValueError(f"invalid cursor {field}")
            if self.pinned_snapshot_id is not None and not isinstance(
                self.pinned_snapshot_id, UUID
            ):
                try:
                    object.__setattr__(
                        self, "pinned_snapshot_id", UUID(str(self.pinned_snapshot_id))
                    )
                except (TypeError, ValueError) as error:
                    raise ValueError("invalid pinned snapshot") from error
        fingerprint = (
            self.filter_fingerprint
            if isinstance(self.filter_fingerprint, FilterFingerprint)
            else FilterFingerprint(self.filter_fingerprint)
        )
        if (
            not isinstance(self.last_key, str)
            or not 1 <= len(self.last_key) <= 255
            or not self.last_key.strip()
            or self.last_key != self.last_key.strip()
        ):
            raise ValueError("invalid search cursor key")
        try:
            last_id = self.last_id if isinstance(self.last_id, UUID) else UUID(str(self.last_id))
        except (AttributeError, TypeError, ValueError) as error:
            raise ValueError("invalid search cursor UUID") from error
        object.__setattr__(self, "filter_fingerprint", fingerprint)
        object.__setattr__(self, "last_id", last_id)

    @property
    def filter_hash(self) -> str:
        return self.filter_fingerprint.value
