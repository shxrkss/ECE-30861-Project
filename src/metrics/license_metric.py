from metrics.base import MetricBase

class LicenseMetric(MetricBase):
    def __init__(self) -> None:
        super().__init__("license")

    def compute(self, url) -> float:
        """Implement licnese check using llm"""
        raise NotImplementedError
