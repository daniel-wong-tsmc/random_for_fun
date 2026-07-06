from gpu_agent.dashboard.report_calls import parse_calls


def _load():
    with open("tests/dashboard/fixtures/report-2026-07-06.txt", encoding="utf-8", errors="replace") as fh:
        return fh.read()


def test_parses_all_fourteen_calls():
    calls = parse_calls(_load())
    assert len(calls) == 14


def test_first_call_fields():
    calls = parse_calls(_load())
    c = next(c for c in calls if c["name"].startswith("Export control"))
    assert c["status"] == "intact"
    assert c["direction"] == "reaffirmed"
    assert c["conviction"] == "high"
    assert c["cycles"] == 2
    assert c["slug"] == "export-control-exposure"
    assert "Export-control policy" in c["statement"]
    assert c["source_count"] == 1


def test_detects_challenged_and_official_and_early():
    calls = parse_calls(_load())
    challenged = [c for c in calls if c["status"] == "challenged"]
    assert any("Custom ASIC" in c["name"] for c in challenged)
    assert any(c["has_official"] for c in calls)   # "incl. company filing / official post"
    assert any(c["early"] for c in calls)          # "early — not yet corroborated"
