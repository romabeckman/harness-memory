__all__ = ["GetDependenciesHandler", "GetDependenciesInput", "GetDependenciesOutput"]


def __getattr__(name: str):
    if name == "GetDependenciesHandler":
        from .handler import GetDependenciesHandler

        return GetDependenciesHandler
    if name == "GetDependenciesInput":
        from .inbound import GetDependenciesInput

        return GetDependenciesInput
    if name == "GetDependenciesOutput":
        from .outbound import GetDependenciesOutput

        return GetDependenciesOutput
    raise AttributeError(name)
