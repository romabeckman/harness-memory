class ProjectSearchFailure(RuntimeError):
    def __init__(self) -> None:
        super().__init__("project search failed")
