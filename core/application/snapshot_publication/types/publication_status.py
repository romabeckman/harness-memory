from enum import Enum


class PublicationStatus(str, Enum):
    ACTIVATED = "ACTIVATED"
    ALREADY_PUBLISHED = "ALREADY_PUBLISHED"
