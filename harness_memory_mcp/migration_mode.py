from enum import StrEnum


class MigrationMode(StrEnum):
    UPGRADE = "upgrade"
    STATUS = "status"
