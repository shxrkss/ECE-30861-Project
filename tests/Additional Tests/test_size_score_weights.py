def collapse(weights: dict, device: dict):
    # mirrors netscore device-weight collapse logic
    def clamp(x): return 0.0 if x < 0 else 1.0 if x > 1 else x
    return sum(weights[k]*clamp(device.get(k,0.0)) for k in weights)

def test_device_weight_biases_small_devices_more():
    W = {"raspberry_pi":0.30,"jetson_nano":0.25,"desktop_pc":0.20,"aws_server":0.25}
    # model fits only on desktop/aws -> small devices 0, large devices 1
    v = collapse(W, {"raspberry_pi":0,"jetson_nano":0,"desktop_pc":1,"aws_server":1})
    assert 0.40 <= v <= 0.50
