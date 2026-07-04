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


SKILL = pathlib.Path(".claude/skills/gather-category/SKILL.md")


def test_gather_skill_wires_web_reach():
    text = SKILL.read_text(encoding="utf-8")
    assert "registry/web-reach-tools.json" in text
    assert "web-reach health check" in text  # the preamble heading
    assert "agent-reach" in text


DOC = pathlib.Path("docs/web-reach.md")
CHARTER = pathlib.Path("docs/agent-swarm-charter.md")


def test_web_reach_doc_exists_and_points_at_registry():
    assert DOC.exists()
    assert "registry/web-reach-tools.json" in DOC.read_text(encoding="utf-8")


def test_charter_part37_documents_web_reach():
    assert "web-reach layer" in CHARTER.read_text(encoding="utf-8").lower()
