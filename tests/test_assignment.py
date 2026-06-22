from gpu_agent.assignment import load_assignment

def test_loads_gpu_assignment():
    a = load_assignment("fixtures/asg.chips.merchant-gpu.json")
    assert a.id == "asg.chips.merchant-gpu"
    assert "nvidia" in a.entities and "amd" in a.entities and "intel" in a.entities
    assert a.weights["D2"] > 0
