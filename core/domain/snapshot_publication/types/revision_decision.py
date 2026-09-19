from enum import Enum


class RevisionDecision(str, Enum):
    ACTIVATE = "ACTIVATE"
    ALREADY_PUBLISHED = "ALREADY_PUBLISHED"
