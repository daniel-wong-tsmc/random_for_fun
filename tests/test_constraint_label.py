"""F67: additive-optional CategoryStatus.constraintLabel."""
import json
from gpu_agent.schema.scorecard import CategoryStatus
from gpu_agent.judgment import prompt as jprompt


def test_constraint_label_optional_roundtrip():
    cs = CategoryStatus(rating="Strong", direction="improving",
                        bottleneck="bottleneck", reason="r")
    assert cs.constraintLabel is None          # absent → None, old payloads valid
    cs2 = CategoryStatus(rating="Strong", direction="improving",
                         bottleneck="bottleneck", reason="r",
                         constraintLabel="CoWoS/HBM3E advanced packaging")
    assert "CoWoS" in cs2.constraintLabel
    assert "constraintLabel" in json.loads(cs2.model_dump_json())


def test_system_prompt_carries_voice_rules_and_constraint_label():
    sys = jprompt.build_system()
    assert "constraintLabel" in sys
    assert "exactly three sentences" in sys        # narrative rule
    assert "at most two sentences" in sys          # rationale rule
    assert "active voice" in sys                   # stop-slop core
    assert "TSMC executive" in sys                 # reader contract
