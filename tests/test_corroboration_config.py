import json
from gpu_agent.config import min_distinct_publishers


def test_registry_value_is_three():
    # N=3 was a user decision (spec, decision provenance fork 2). The three amended
    # SYSTEM prompts hardcode "3 distinct publishers"; if you tune the registry value,
    # this test forces you to update those prompts (and re-run the eval) too.
    assert min_distinct_publishers() == 3
    raw = json.load(open("registry/corroboration.json", encoding="utf-8"))
    assert raw == {"minDistinctPublishers": 3}


def test_missing_file_falls_back_to_three(monkeypatch, tmp_path):
    import gpu_agent.config as config
    monkeypatch.setattr(config, "CORROBORATION_PATH", str(tmp_path / "absent.json"))
    config.min_distinct_publishers.cache_clear()
    try:
        assert config.min_distinct_publishers() == 3
    finally:
        config.min_distinct_publishers.cache_clear()
