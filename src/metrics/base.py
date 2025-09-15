class MetricBase():
    def __init__(self, name: str) -> None:
        self.name = name
        self.value = 0.0

    def compute(self, url) -> float:
        """Compute metric given URL + metadata."""
        raise NotImplementedError

    def is_applicable(self, url) -> bool:
        """Default: applicable to all."""
        return True
