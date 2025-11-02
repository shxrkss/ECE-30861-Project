def has_required_fields(doc: dict):
    keys = {
        "name","category","net_score","net_score_latency",
        "ramp_up_time","ramp_up_time_latency",
        "bus_factor","bus_factor_latency",
        "performance_claims","performance_claims_latency",
        "license","license_latency",
        "size_score","size_score_latency",
        "dataset_and_code_score","dataset_and_code_score_latency",
        "dataset_quality","dataset_quality_latency",
        "code_quality","code_quality_latency",
    }
    return keys.issubset(doc.keys())

def test_schema_keys_present_on_sample():
    sample = {
      "name":"m", "category":"MODEL",
      "net_score":0.0,"net_score_latency":0,
      "ramp_up_time":0.0,"ramp_up_time_latency":0,
      "bus_factor":0.0,"bus_factor_latency":0,
      "performance_claims":0.0,"performance_claims_latency":0,
      "license":0.0,"license_latency":0,
      "size_score":{"raspberry_pi":0,"jetson_nano":0,"desktop_pc":0,"aws_server":0},
      "size_score_latency":0,
      "dataset_and_code_score":0.0,"dataset_and_code_score_latency":0,
      "dataset_quality":0.0,"dataset_quality_latency":0,
      "code_quality":0.0,"code_quality_latency":0,
    }
    assert has_required_fields(sample)
