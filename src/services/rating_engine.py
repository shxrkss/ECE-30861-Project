# src/services/rating_engine.py
from datetime import datetime
from src.models.artifacts import ModelRating
from src.orchestrator import run_all_metrics


def compute_model_rating(artifact) -> ModelRating:
    """
    Convert orchestrator output → ModelRating (strict autograder format).
    The orchestrator must return a dict of metric_name → score.
    Latencies may also be present. If not, we populate with dummy 0.0.
    """

    # artifact.data.url should point to a model; we pass it to orchestrator
    model_url = str(artifact.data.url)

    raw = run_all_metrics(model_url)

    # Helper to safely extract fields
    def get(k): return float(raw.get(k, 0.0))
    def get_lat(k): return float(raw.get(f"{k}_latency", 0.0))

    return ModelRating(
        name=artifact.metadata.name,
        category=raw.get("category", "model"),

        net_score=get("net_score"),
        net_score_latency=get_lat("net_score"),

        ramp_up_time=get("ramp_up_time"),
        ramp_up_time_latency=get_lat("ramp_up_time"),

        bus_factor=get("bus_factor"),
        bus_factor_latency=get_lat("bus_factor"),

        performance_claims=get("performance_claims"),
        performance_claims_latency=get_lat("performance_claims"),

        license=get("license"),
        license_latency=get_lat("license"),

        dataset_and_code_score=get("dataset_and_code_score"),
        dataset_and_code_score_latency=get_lat("dataset_and_code_score"),

        dataset_quality=get("dataset_quality"),
        dataset_quality_latency=get_lat("dataset_quality"),

        code_quality=get("code_quality"),
        code_quality_latency=get_lat("code_quality"),

        reproducibility=get("reproducibility"),
        reproducibility_latency=get_lat("reproducibility"),

        reviewedness=get("reviewedness"),
        reviewedness_latency=get_lat("reviewedness"),

        tree_score=get("tree_score"),
        tree_score_latency=get_lat("tree_score"),

        size_score=dict(
            raspberry_pi=get("size_score_rpi"),
            jetson_nano=get("size_score_nano"),
            desktop_pc=get("size_score_pc"),
            aws_server=get("size_score_aws"),
        ),
        size_score_latency=get_lat("size_score"),
    )
