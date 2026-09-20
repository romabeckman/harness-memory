import re
from collections.abc import Callable, Sequence
from typing import TextIO

from core.infrastructure.postgres.migrations import MigrationStatus


class MigrationCLI:
    def __init__(
        self,
        upgrade: Callable[[], MigrationStatus],
        status: Callable[[], MigrationStatus],
        output: TextIO,
    ):
        self._upgrade = upgrade
        self._status = status
        self._output = output

    def dispatch(self, arguments: Sequence[str]) -> int:
        if not arguments or arguments[0] != "migrate":
            self._write("error: expected 'migrate' command")
            return 2
        options = list(arguments[1:])
        if any(option != "--status" for option in options) or options.count("--status") > 1:
            self._write("error: unsupported migrate option")
            return 2
        try:
            result = self._status() if "--status" in options else self._upgrade()
            if "--status" in options:
                self._write_status(result)
            return 0
        except Exception as error:
            self._write(f"error: {self._redact(str(error))}")
            return 1

    def _write_status(self, status: MigrationStatus) -> None:
        current = status.current_revision or "<none>"
        state = "current" if status.is_current else "pending"
        self._write(f"current: {current}")
        self._write(f"head: {status.head_revision}")
        self._write(f"status: {state}")

    def _write(self, message: str) -> None:
        self._output.write(f"{message}\n")

    @staticmethod
    def _redact(message: str) -> str:
        redacted = re.sub(
            r"(postgres(?:ql)?(?:\+[a-z0-9_]+)?://)[^@\s]+@",
            r"\1<redacted>@",
            message,
            flags=re.IGNORECASE,
        )
        redacted = re.sub(r"(?i)(password|passwd|pwd)=([^\s&]+)", r"\1=<redacted>", redacted)
        return re.sub(
            r"(?i)(for user\s+)[\"']?[^\"'\s]+[\"']?",
            r"\1<redacted>",
            redacted,
        )
