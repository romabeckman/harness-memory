__all__ = ["GetContextHandler", "GetContextInput", "GetContextOutput"]


def __getattr__(name: str):
    if name == "GetContextHandler":
        from .handler import GetContextHandler

        return GetContextHandler
    if name == "GetContextInput":
        from .inbound import GetContextInput

        return GetContextInput
    if name == "GetContextOutput":
        from .outbound import GetContextOutput

        return GetContextOutput
    raise AttributeError(name)
