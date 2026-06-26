from gpu_agent.assignment import load_assignment

def test_assignment_has_category():
    a = load_assignment("fixtures/asg.chips.merchant-gpu.json")
    assert a.category == "chips.merchant-gpu"
