import json, os
from gpu_agent.dashboard.build import build_dashboard

FIX = "tests/dashboard/fixtures"

def test_end_to_end_writes_html_and_summary(tmp_path):
    # Arrange a mini work dir containing the fixture report.
    work = tmp_path / "work" / "daily-2026-07-06"
    work.mkdir(parents=True)
    with open(f"{FIX}/report-2026-07-06.txt", encoding="utf-8", errors="replace") as fh:
        (work / "report.txt").write_text(fh.read(), encoding="utf-8")
    out = tmp_path / "dashboard.html"
    summary = build_dashboard(
        category_id="chips.merchant-gpu", store_dir=FIX,
        work_dir=str(tmp_path / "work"), plain_path=f"{FIX}/plain-2026-07-06.json",
        out_path=str(out), generated_at="2026-07-06 09:20")
    assert out.exists()
    html = out.read_text(encoding="utf-8")
    assert 'id="calls"' in html and 'id="top-signals"' in html
    assert summary["runs"] == 4
    assert summary["claims"] == 14
    assert summary["auto_simplified"] >= 1   # most sentences have no fixture rewrite

def test_generated_html_has_no_slop_or_raw_cowos(tmp_path):
    work = tmp_path / "work" / "daily-2026-07-06"
    work.mkdir(parents=True)
    with open(f"{FIX}/report-2026-07-06.txt", encoding="utf-8", errors="replace") as fh:
        (work / "report.txt").write_text(fh.read(), encoding="utf-8")
    out = tmp_path / "dashboard.html"
    build_dashboard(category_id="chips.merchant-gpu", store_dir=FIX,
                    work_dir=str(tmp_path / "work"), plain_path=f"{FIX}/plain-2026-07-06.json",
                    out_path=str(out), generated_at="2026-07-06 09:20")
    html = out.read_text(encoding="utf-8")
    for w in ["delve", "leverage", "seamless", "boasts"]:
        assert w not in html.lower()
    # Scope to the "Key claims" section (which contains the breaks_if expanders);
    # the Plain-language guide table intentionally lists raw terms like "CoWoS".
    calls_html = html[html.index('id="calls"'):html.index('id="demand-supply"')]
    assert "CoWoS" not in calls_html                      # breaks_if jargon must be term-swapped
    assert "advanced chip packaging" in calls_html        # proof it was swapped in place
