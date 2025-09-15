from metrics.base import MetricBase
import math

class SizeMetric(MetricBase):
    def __init__(self) -> None:
        super().__init__("size")

    # need to replace param with whatever is needed to compute size
    def compute(self, url, param) -> float:
        """Compute size metric using using calcuation"""

        size_score = (math.log(param) - 15) / 10

        return size_score
