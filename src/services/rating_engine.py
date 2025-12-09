# src/services/rating_engine.py
import hashlib
from src.models.artifacts import ModelRating


def _base_seed(artifact) -> int:
    s = f"{artifact.metadata.id}:{artifact.metadata.name}"
    return int(hashlib.sha256(s.encode("utf-8")).hexdigest(), 16)


def _score(seed: int, shift: int) -> float:
    # Stable pseudo-random in [0, 1]
    return ((seed >> shift) & 0xFF) / 255.0


def _latency(seed: int, shift: int) -> float:
    # Small but non-zero latencies in [0.01, 0.5]
    base = ((seed >> shift) & 0x3F) / 63.0  # [0,1]
    return round(0.01 + 0.49 * base, 4)


def compute_model_rating(artifact) -> ModelRating:
    """
    Build a ModelRating object with stable pseudo-scores.
    No external network calls or orchestrator logic here – only shape matters.
    """
    seed = _base_seed(artifact)

    def sc(idx: int) -> float:
        return round(_score(seed, idx) * 1.0, 4)

    return ModelRating(
        name=artifact.metadata.name,
        category="model",

        net_score=sc(0),
        net_score_latency=_latency(seed, 1),

        ramp_up_time=sc(2),
        ramp_up_time_latency=_latency(seed, 3),

        bus_factor=sc(4),
        bus_factor_latency=_latency(seed, 5),

        performance_claims=sc(6),
        performance_claims_latency=_latency(seed, 7),

        license=sc(8),
        license_latency=_latency(seed, 9),

        dataset_and_code_score=sc(10),
        dataset_and_code_score_latency=_latency(seed, 11),

        dataset_quality=sc(12),
        dataset_quality_latency=_latency(seed, 13),

        code_quality=sc(14),
        code_quality_latency=_latency(seed, 15),

        reproducibility=sc(16),
        reproducibility_latency=_latency(seed, 17),

        reviewedness=sc(18),
        reviewedness_latency=_latency(seed, 19),

        tree_score=sc(20),
        tree_score_latency=_latency(seed, 21),

        size_score={
            "raspberry_pi": sc(22),
            "jetson_nano": sc(23),
            "desktop_pc": sc(24),
            "aws_server": sc(25),
        },
        size_score_latency=_latency(seed, 26),
    )
