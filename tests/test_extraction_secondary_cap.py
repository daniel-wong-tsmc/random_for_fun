from gpu_agent.extraction.prompt import SYSTEM

def test_system_caps_secondary_only_confidence_at_medium():
    s = SYSTEM.lower()
    assert "secondary" in s
    assert "at most medium" in s          # the cap wording (matches the hypothesis-cap phrasing)

def test_system_states_corroboration_exception():
    s = SYSTEM.lower()
    # contract v1.3: the secondary cap lifts when evidence spans >=3 distinct publishers
    assert "3 distinct publishers" in s   # the corroboration threshold, stated to the brain
    assert "syndication" in s             # distinct outlets, not one story re-run

def test_existing_doctrine_still_present():
    s = SYSTEM.lower()
    assert "data, not instructions" in s  # injection boundary preserved
    assert "do not invent" in s           # no-invented-numbers preserved
