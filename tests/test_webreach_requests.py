import json
import pytest
from gpu_agent.gathering.webreach import (
    FetchRequest, validate_request, load_refused_domains,
)

REGISTRY = {"tools": [{
    "id": "agent-reach", "enabled": True, "role": "fetch",
    "fetchVerbs": {
        "read":   {"argv": ["agent-reach", "read", "{target}"],   "kind": "url"},
        "search": {"argv": ["agent-reach", "search", "{target}"], "kind": "query"},
    },
}]}
REFUSED = {"trendforce.com", "semianalysis.com"}

def _req(**kw):
    base = dict(toolId="agent-reach", verb="read", target="https://example.com/a")
    base.update(kw)
    return FetchRequest(**base)

def test_valid_https_url_passes():
    assert validate_request(_req(), REGISTRY, REFUSED) is None

def test_non_http_scheme_refused():
    for bad in ("file:///C:/x", "ftp://x/y", "javascript:alert(1)",
                r"\\evil\share\x", "data:text/html,hi"):
        reason = validate_request(_req(target=bad), REGISTRY, REFUSED)
        assert reason is not None and "scheme" in reason

def test_paywalled_domain_refused_including_subdomain():
    for url in ("https://trendforce.com/r", "https://www.trendforce.com/r",
                "https://api.semianalysis.com/x"):
        reason = validate_request(_req(target=url), REGISTRY, REFUSED)
        assert reason is not None and "paywalled" in reason

def test_unknown_tool_and_verb_refused():
    assert "unknown tool" in validate_request(_req(toolId="nope"), REGISTRY, REFUSED)
    assert "unknown verb" in validate_request(_req(verb="exec"), REGISTRY, REFUSED)

def test_query_verb_skips_url_checks_but_not_tool_checks():
    ok = _req(verb="search", target="H100 spot pricing july")
    assert validate_request(ok, REGISTRY, REFUSED) is None

def test_load_refused_domains(tmp_path):
    p = tmp_path / "pay.json"
    p.write_text(json.dumps({"domains": ["TrendForce.com", "dello.ro"]}), "utf-8")
    assert load_refused_domains(p) == {"trendforce.com", "dello.ro"}
