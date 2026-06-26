from gpu_agent.cycle import AssignmentProvider

def test_path_for_uses_asg_convention():
    p = AssignmentProvider("fixtures")
    assert p.path_for("chips.merchant-gpu").name == "asg.chips.merchant-gpu.json"

def test_get_returns_assignment_when_file_exists():
    a = AssignmentProvider("fixtures").get("chips.merchant-gpu")
    assert a is not None
    assert a.category == "chips.merchant-gpu"

def test_get_returns_none_when_missing():
    assert AssignmentProvider("fixtures").get("energy.cooling") is None
