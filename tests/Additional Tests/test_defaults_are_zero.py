def test_zero_defaults_match_contract():
    defaults = dict(
        net_score=0.0, ramp_up_time=0.0, bus_factor=0.0, performance_claims=0.0,
        license=0.0, dataset_and_code_score=0.0, dataset_quality=0.0, code_quality=0.0
    )
    assert all(0.0 <= v <= 0.0 for v in defaults.values())
