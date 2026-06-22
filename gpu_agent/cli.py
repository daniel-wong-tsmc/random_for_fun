from __future__ import annotations
import argparse, json, pathlib, sys
from gpu_agent.assignment import load_assignment
from gpu_agent.schema.finding import Finding, Confidence
from gpu_agent.schema.scorecard import DimensionRating
from gpu_agent.pipeline import build_scorecard
from gpu_agent.gate import GateError
from gpu_agent.store import JsonStore

def _build(args):
    a = load_assignment(args.assignment)
    fx = pathlib.Path(args.fixtures)
    findings = [Finding.model_validate(d) for d in json.loads((fx / "findings.json").read_text("utf-8"))]
    ratings = {k: DimensionRating.model_validate(v)
               for k, v in json.loads((fx / "ratings.json").read_text("utf-8")).items()}
    anchors = json.loads((fx / "anchors.json").read_text("utf-8"))
    return build_scorecard(findings, ratings, anchors, a, "MVP scorecard.",
                           Confidence(level="medium", basis="fixture run"))

def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="gpu-agent")
    sub = p.add_subparsers(dest="cmd", required=True)
    for name in ("run", "score"):           # ingest/extract/judge register in the adapter plan (spec §13.5)
        sp = sub.add_parser(name)
        sp.add_argument("--assignment", required=True)
        sp.add_argument("--fixtures", required=True, help="dir with findings.json, ratings.json, anchors.json")
        if name == "run":
            sp.add_argument("--out", default="store")
    args = p.parse_args(argv)
    try:
        sc = _build(args)
    except GateError as e:
        print("GATE FAILED:", *e.violations, sep="\n  ", file=sys.stderr)
        return 1
    summary = f"DMI={sc.demandSupply.dmiContribution:.3f} SMI={sc.demandSupply.smiContribution:.3f}"
    if args.cmd == "score":                 # run a process in isolation: compute, print, don't persist
        print(summary)
        return 0
    path = JsonStore(pathlib.Path(args.out)).append(sc)
    print(f"wrote {path}  {summary}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
