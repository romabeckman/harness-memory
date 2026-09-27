from typing import Annotated

from pydantic import BaseModel, StringConstraints


EnvironmentNameInput = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=1,
        max_length=64,
        pattern=r"^[a-zA-Z0-9_-]+$",
    ),
]


class ProjectEnvironmentCreate(BaseModel):
    name: EnvironmentNameInput
