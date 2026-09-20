from enum import Enum


class EntityType(str, Enum):
    PROJECT = "project"
    SYSTEM = "system"
    SERVICE = "service"
    API = "api"
    EVENT = "event"
    LIBRARY = "library"
    TEAM = "team"
