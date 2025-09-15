from metrics.base import MetricBase
import math

class BusMetric(MetricBase):
    def __init__(self) -> None:
        super().__init__("ramp_up")

    # need to replace N, C, and ci with whatever is needed to compute bus factor
    # N = total number of contributors
    # C = total number of commits
    # ci = contribution per contributor
    def compute(self, url, N, C, ci) -> float:
        """Compute ramp up time metric using using calcuation"""

        sum_of_squared_factors = 0
        for contributions in ci:
            sum_of_squared_factors += (contributions / C) ** 2
        
        bus_factor = (N * sum_of_squared_factors) / (N - 1)

        return bus_factor
