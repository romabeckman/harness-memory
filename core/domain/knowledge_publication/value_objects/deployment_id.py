from dataclasses import dataclass


@dataclass(frozen=True)
class DeploymentId:
    value: str

    def __post_init__(self) -> None:
        trimmed = self.value.strip()
        if not trimmed:
            raise ValueError("deployment_id must not be empty")
        if len(self.value) > 255:
            raise ValueError("deployment_id exceeds maximum length")
