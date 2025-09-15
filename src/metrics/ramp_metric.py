from metrics.base import MetricBase
import math

class RampMetric(MetricBase):
    def __init__(self) -> None:
        super().__init__("ramp_up")

    # need to replace downloads with whatever is needed to compute ramp up time
    def compute(self, url, downloads) -> float:
        """Compute ramp up time metric using using calcuation"""

        ramp_score = (math.log(downloads) - 15) / 10

        return ramp_score
