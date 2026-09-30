from typing import Protocol

from core.application.environment_context.use_cases.get_history.inbound import GetHistoryInput


class EnvironmentHistoryRepository(Protocol):
    def get_history(self, request: GetHistoryInput) -> dict: ...
