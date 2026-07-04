import json
import pathlib

REGISTRY = pathlib.Path("registry/web-reach-tools.json")


def _load():
    return json.loads(REGISTRY.read_text(encoding="utf-8"))


def test_registry_parses_and_has_version():
    data = _load()
    assert data["version"] == 1
    assert isinstance(data["tools"], list) and data["tools"]


def test_tool_ids_are_unique():
    ids = [t["id"] for t in _load()["tools"]]
    assert len(ids) == len(set(ids))


def test_agent_reach_is_registered_and_enabled():
    ar = next((t for t in _load()["tools"] if t["id"] == "agent-reach"), None)
    assert ar is not None
    assert ar["enabled"] is True


def test_enabled_tools_have_required_fields():
    for t in _load()["tools"]:
        if not t.get("enabled"):
            continue
        assert t.get("healthCmd"), f"{t['id']} missing healthCmd"
        assert t.get("installDocUrl"), f"{t['id']} missing installDocUrl"
        caps = t.get("capabilities")
        assert isinstance(caps, list) and caps, f"{t['id']} missing capabilities"
