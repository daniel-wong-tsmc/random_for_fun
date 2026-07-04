"""F62 — emitted judge/thesis rows carry the finding's observation date so a brain
judging a mixed-vintage corpus can weigh old vs new. The frozen internal judge path
(include_dates default False) stays byte-identical."""
import json
import subprocess
import sys

from gpu_agent.judgment.briefing import build_briefing
from gpu_agent.judgment.prompt import build_user_prompt
from gpu_agent.registry.indicators import IndicatorRegistry
from gpu_agent.schema.finding import Confidence, Evidence, Finding, Impact
from gpu_agent.thesis import _finding_lines

REGISTRY = IndicatorRegistry.load("registry/indicators.json")


# local finding factory — repo convention, same shape as tests/test_corpus_enumerate.py's
def _f(fid, entity="NVDA", indicatorId="designWins", as_of="2026-07-02",
       observedAt="2026-07-01"):
    return Finding(
        id=fid, statement=f"s-{fid}", kind="observed", trend="rising", why="w",
        impact=Impact(targets=["chips.merchant-gpu"], direction="positive", mechanism="m"),
        evidence=[Evidence(source="src", url="https://x.example/a", date=observedAt,
                           excerpt="e", tier="secondary")],
        confidence=Confidence(level="medium", basis="b"), asOf=as_of,
        indicatorId=indicatorId, side="structural", polarityDemand=1, polaritySupply=0,
        magnitude=2, entity=entity, observedAt=observedAt,
        capturedAt=f"{as_of}T00:00:00Z")


def _run(*args):
    return subprocess.run([sys.executable, "-m", "gpu_agent.cli", *args],
                          capture_output=True, text=True)


def _briefing():
    return build_briefing([_f("doc-1", indicatorId="designWins",
                              observedAt="2026-06-29")],
                          REGISTRY, "chips.merchant-gpu")


def test_default_byte_identical_without_dates():
    b = _briefing()
    assert build_user_prompt(b) == build_user_prompt(b, include_dates=False)
    assert "observed=" not in build_user_prompt(b)


def test_include_dates_appends_observed_inside_parens():
    row_lines = [l for l in build_user_prompt(_briefing(), include_dates=True).splitlines()
                 if l.strip().startswith("doc-1")]
    assert len(row_lines) == 1
    assert row_lines[0].endswith("conf=medium observed=2026-06-29)")


def test_thesis_rows_carry_observed():
    lines = _finding_lines([_f("doc-1", observedAt="2026-06-29")])
    assert lines[0].endswith("conf=medium observed=2026-06-29)")


def test_judge_emit_cli_carries_observed(tmp_path):
    findings = [_f("doc-1", observedAt="2026-06-29")]
    p = tmp_path / "findings.json"
    p.write_text(json.dumps([f.model_dump() for f in findings]), "utf-8")
    out = _run("judge", "--emit-prompt", "--findings", str(p),
               "--category", "chips.merchant-gpu", "--store", str(tmp_path / "store"))
    assert out.returncode == 0, out.stderr
    bundle = json.loads(out.stdout)
    assert "observed=2026-06-29" in bundle["user"]


def test_thesis_emit_cli_carries_observed(tmp_path):
    findings = [_f("doc-1", observedAt="2026-06-29")]
    p = tmp_path / "findings.json"
    p.write_text(json.dumps([f.model_dump() for f in findings]), "utf-8")
    out = _run("thesis", "--findings", str(p), "--store", str(tmp_path / "store"),
               "--category", "chips.merchant-gpu", "--as-of", "2026-07",
               "--emit-prompt", "--seed", "registry/theses.chips.merchant-gpu.json")
    assert out.returncode == 0, out.stderr
    bundle = json.loads(out.stdout)
    assert "observed=2026-06-29" in bundle["user"]
