from enum import Enum


class RelationType(str, Enum):
    PART_OF = "part_of"
    OWNED_BY = "owned_by"
    PROVIDES = "provides"
    CONSUMES = "consumes"
    DEPENDS_ON = "depends_on"
    PUBLISHES = "publishes"
    SUBSCRIBES_TO = "subscribes_to"
    IMPLEMENTS = "implements"
