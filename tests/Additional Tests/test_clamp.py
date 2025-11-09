def clamp01(x):
    try:
        x = float(x)
    except Exception:
        return 0.0
    return 0.0 if x < 0 else 1.0 if x > 1 else x

def test_clamp_in_range():
    assert clamp01(0.5) == 0.5

def test_clamp_under_over():
    assert clamp01(-1.0) == 0.0
    assert clamp01(2.7) == 1.0

def test_clamp_non_numeric():
    assert clamp01("NaN-ish") == 0.0
