import os
import time
import json
import logging
from metrics.base import MetricBase
from src.metrics.lineage import get_lineage  # <- assuming you put your helper there


class TreeScoreMetric(MetricBase):
    """
    Computes TreeScore: how completely a model's ancestry is declared.
    Uses recursive config.json traversal to assess lineage depth and completeness.
    """

    def __init__(self):
        super().__init__("tree_score")

    def _is_complete_lineage(self, lineage, registry_root) -> bool:
        """
        Verifies that each node in the lineage has a valid config.json
        containing base_model_name_or_path or None if root.
        """
        for model_name in lineage:
            cfg_path = os.path.join(registry_root, model_name, "config.json")
            if not os.path.exists(cfg_path):
                logging.warning(f"[TreeScore] Missing config for {model_name}")
                return False
            with open(cfg_path, "r") as f:
                cfg = json.load(f)
            # last model can omit base_model_name_or_path
            if model_name != lineage[-1] and "base_model_name_or_path" not in cfg:
                logging.warning(f"[TreeScore] Missing base_model_name_or_path for {model_name}")
                return False
        return True

    def compute(self, model_dir: str, registry_root: str) -> tuple[float, int]:
        """
        Compute TreeScore given a model directory and registry root.
        Returns (score, latency_ms)
        """
        start = time.time()
        logging.info(f"[TreeScore] Starting computation for {model_dir}")

        try:
            lineage = get_lineage(model_dir, registry_root)
            num_nodes = len(lineage)
            logging.debug(f"[TreeScore] Lineage chain: {lineage}")

            if num_nodes == 0:
                score = 0.0
            elif num_nodes == 1:
                score = 0.5
            else:
                score = 1.0 if self._is_complete_lineage(lineage, registry_root) else 0.5

            latency = int((time.time() - start) * 1000)
            logging.info(f"[TreeScore] Computed score={score} (latency={latency}ms)")
            return score, latency

        except Exception as e:
            logging.error(f"[TreeScore] Failed to compute metric: {e}")
            return 0.0, 0