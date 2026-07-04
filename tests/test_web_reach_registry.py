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
    # guard the doctrinal payload of the gatherer contract, not just the wiring
    assert "chase it toward a primary" in text
    assert "secondary" in text


DOC = pathlib.Path("docs/web-reach.md")
CHARTER = pathlib.Path("docs/agent-swarm-charter.md")


def test_web_reach_doc_exists_and_points_at_registry():
    assert DOC.exists()
    assert "registry/web-reach-tools.json" in DOC.read_text(encoding="utf-8")


def test_charter_part37_documents_web_reach():
    text = CHARTER.read_text(encoding="utf-8")
    assert "web-reach layer" in text.lower()
    # guard the complementary-not-replacement doctrine in the charter, not just the heading
    assert "complementary, never a replacement" in text


# --- F70: last30days (discovery-role) ---

VALID_ROLES = {"fetch", "discovery"}


def test_every_enabled_tool_has_valid_role():
    for t in _load()["tools"]:
        if not t.get("enabled"):
            continue
        assert t.get("role") in VALID_ROLES, f"{t['id']} role={t.get('role')!r} not in {VALID_ROLES}"


def test_last30days_registered_as_discovery():
    t = next((x for x in _load()["tools"] if x["id"] == "last30days"), None)
    assert t is not None
    assert t["enabled"] is True
    assert t["role"] == "discovery"


def test_skill_and_charter_document_discovery_role():
    skill = SKILL.read_text(encoding="utf-8")
    charter = CHARTER.read_text(encoding="utf-8")
    # discovery-role tools are leads-only, never ingested as blobs
    assert "role: discovery" in skill
    assert "leads only" in skill.lower()
    assert "last30days" in skill
    assert "discovery" in charter.lower()


def test_gatherer_contract_and_round_building_are_role_aware():
    # the step-3 SUBAGENT contract (not just the coordinator preamble) must be role-aware,
    # and discovery tools must have a concrete leads-only home in round building — else a
    # fetch subagent could ingest last30days' synthesized brief as a secondary blob.
    skill = SKILL.read_text(encoding="utf-8")
    assert "role: fetch" in skill            # contract scoped to fetch tools
    assert "Discovery-role leads" in skill   # step 2b — the concrete home
    assert "Never add the synthesized brief" in skill  # never-ingest rule in the actionable step
