"""Surface the REAL conflicts hidden behind `judge --recorded` (or `pipeline
--recorded-judge`) dying with `LLMError: no recorded response for this call`.

Why that error hides the cause: judge_findings() detects anchor/citation
conflicts, then RESAMPLES (resample_budget=2). In recorded mode the
RecordedClient has no more answers, so the resample raises LLMError before the
conflict list is ever printed. This script replays the same answers once with
resample_budget=0, which makes judge_findings raise JudgmentError carrying the
actual violations.

READ-ONLY: judges in memory; writes nothing to store/ or work/.

Usage (from repo root, CWD matters — registry paths are relative):
  .venv/Scripts/python .claude/skills/desk-debugging-playbook/scripts/judge_conflicts.py \
      <findings.json> <judge-answer.json> <categoryId>

Exit codes: 0 = aggregates cleanly, 1 = conflicts/violations printed, 2 = usage.
"""
from __future__ import annotations
import json
import pathlib
import sys


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print(__doc__, file=sys.stderr)
        return 2
    findings_path, answers_path, category = argv

    from gpu_agent.config import REGISTRY_PATH
    from gpu_agent.judgment.judge import JudgmentError, judge_findings
    from gpu_agent.llm.recorded import RecordedClient
    from gpu_agent.registry.indicators import IndicatorRegistry
    from gpu_agent.schema.finding import Finding

    findings = [Finding.model_validate(d)
                for d in json.loads(pathlib.Path(findings_path).read_text("utf-8"))]
    answers = json.loads(pathlib.Path(answers_path).read_text("utf-8"))
    if not isinstance(answers, list) or not all(isinstance(a, str) for a in answers):
        print("SHAPE ERROR: the judge answer file must be a JSON array of "
              "serialized-object STRINGS (one per sample), matching "
              "fixtures/recorded/judge-nvda.json. Fix the shape first - this is "
              "not a conflict problem.", file=sys.stderr)
        return 1
    registry = IndicatorRegistry.load(REGISTRY_PATH)
    try:
        judge_findings(findings, RecordedClient(answers), registry, category,
                       samples=len(answers), resample_budget=0)
    except JudgmentError as e:
        print("JUDGMENT CONFLICTS (why the recorded run starved its resample loop):")
        for v in e.violations:
            print(f"  - {v}")
        print("\nRoute: re-dispatch the violating sample(s) per the F38 protocol "
              "(run-cycle SKILL.md) with these lines appended. Never edit the answer.")
        return 1
    except Exception as e:  # noqa: BLE001 — anything else is an answer-shape problem
        print(f"NON-CONFLICT FAILURE (likely answer shape/schema): "
              f"{type(e).__name__}: {e}", file=sys.stderr)
        return 1
    print(f"no conflicts: {len(answers)} recorded sample(s) aggregate cleanly for "
          f"'{category}'. If the CLI still fails, check --samples vs answer count "
          "(exit 2) and the voice-lint/sufficiency gates (exit 1 with prefixed lines).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
