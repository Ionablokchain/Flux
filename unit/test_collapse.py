from flux.tvm.collapse import collapse

def test_max_weight():
    data = [(10, 0.8), (20, 0.2)]
    assert collapse(data, "max_weight") == 10

def test_average():
    data = [(10, 0.8), (20, 0.2)]
    assert collapse(data, "average") == 12.0  # (10*0.8 + 20*0.2)