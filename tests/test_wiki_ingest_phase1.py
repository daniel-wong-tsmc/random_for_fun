import pytest
from gpu_agent.store import FindingStore
from gpu_agent.wiki.store import WikiStore
from gpu_agent.wiki.ingest import slug, route_findings, build_bundle, IngestResult
from gpu_agent.schema.finding import Finding, Kind, Impact, Confidence


def _store(tmp_path):
    return WikiStore(tmp_path / "wiki", FindingStore(tmp_path / "findings"))


def _f(fid, entity, statement="s"):
    return Finding(
        id=fid, statement=statement, kind=Kind.observed, trend="flat", why="w",
        impact=Impact(targets=["x"], direction="negative", mechanism="m"),
        confidence=Confidence(level="medium", basis="b"), asOf="2026-06",
        indicatorId="D2", side="demand", polarityDemand=1, polaritySupply=0,
        magnitude=2, entity=entity, observedAt="2026-06", capturedAt="2026-06-12")


def test_slug_normalizes():
    assert slug("NVDA") == "nvda"
    assert slug("SK hynix") == "sk-hynix"
    assert slug("  TSMC  ") == "tsmc"


def test_slug_empty_raises():
    with pytest.raises(ValueError):
        slug("!!!")


def test_route_creates_entity_pages_and_observations(tmp_path):
    ws = _store(tmp_path)
    touched = route_findings(ws, [_f("f-1", "NVDA"), _f("f-2", "AMD")], as_of="2026-06-28")
    assert touched == ["entity:amd", "entity:nvidia"]   # F24: NVDA resolves; AMD unregistered
    assert {o.findingId for o in ws.observations("entity:nvidia")} == {"f-1"}
    assert ws.get_page("entity:amd").title == "AMD"


def test_route_is_idempotent(tmp_path):
    ws = _store(tmp_path)
    route_findings(ws, [_f("f-1", "NVDA")], as_of="2026-06-28")
    n_events = len(ws.log.read())
    route_findings(ws, [_f("f-1", "NVDA")], as_of="2026-06-28")  # re-run
    assert len(ws.log.read()) == n_events  # no new observation/create events


def test_route_empty_entity_fails_loud(tmp_path):
    ws = _store(tmp_path)
    with pytest.raises(ValueError):
        route_findings(ws, [_f("f-1", "  ")], as_of="2026-06-28")


def test_route_applies_category(tmp_path):
    ws = _store(tmp_path)
    route_findings(ws, [_f("f-1", "NVDA")], as_of="2026-06-28", category="chips.merchant-gpu")
    assert ws.get_page("entity:nvidia").category == "chips.merchant-gpu"


# --- F24 Seam B: entity pages keyed by the resolved canonical id (acceptance 3) ---

def test_route_alias_lands_on_canonical_entity_page(tmp_path):
    ws = _store(tmp_path)
    touched = route_findings(ws, [_f("f-1", "NVDA")], as_of="2026-06-28")
    assert touched == ["entity:nvidia"]
    assert {o.findingId for o in ws.observations("entity:nvidia")} == {"f-1"}
    assert ws.get_page("entity:nvidia").title == "NVIDIA"        # routed title = display name


def test_route_alias_and_canonical_share_one_page(tmp_path):
    ws = _store(tmp_path)
    route_findings(ws, [_f("f-1", "NVDA")], as_of="2026-06-28")
    touched = route_findings(ws, [_f("f-2", "nvidia")], as_of="2026-06-28")
    assert touched == ["entity:nvidia"]                          # no nvda-vs-nvidia split minted
    assert {o.findingId for o in ws.observations("entity:nvidia")} == {"f-1", "f-2"}


def test_route_unregistered_entity_unchanged(tmp_path):
    ws = _store(tmp_path)
    touched = route_findings(ws, [_f("f-1", "Super Micro")], as_of="2026-06-28")
    assert touched == ["entity:super-micro"]                     # plain slug, as today
    assert ws.get_page("entity:super-micro").title == "Super Micro"


def test_build_bundle_has_touched_pages_and_new_findings(tmp_path):
    ws = _store(tmp_path)
    findings = [_f("f-1", "NVDA", "DC revenue up")]
    touched = route_findings(ws, findings, as_of="2026-06-28")
    bundle = build_bundle(ws, findings, touched, as_of="2026-06-28")
    assert bundle["asOf"] == "2026-06-28"
    assert bundle["schema"] == IngestResult.model_json_schema()
    page = bundle["pages"][0]
    assert page["pageId"] == "entity:nvidia"
    assert page["newFindings"][0]["id"] == "f-1"
    assert page["newFindings"][0]["statement"] == "DC revenue up"
    assert "currentBody" in page and "currentState" in page
