from enum import Enum


class PublicationStatus(str, Enum):
    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    ALREADY_PUBLISHED = "ALREADY_PUBLISHED"
