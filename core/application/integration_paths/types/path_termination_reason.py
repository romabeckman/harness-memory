from enum import Enum


class PathTerminationReason(str, Enum):
    COMPLETE = "complete"
    PATH_LIMIT = "path_limit"
    EXPANSION_LIMIT = "expansion_limit"
