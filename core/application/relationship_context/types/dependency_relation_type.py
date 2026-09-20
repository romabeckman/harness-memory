from enum import Enum


class DependencyRelationType(str, Enum):
    DEPENDS_ON = "depends_on"
    CONSUMES = "consumes"
    SUBSCRIBES_TO = "subscribes_to"
