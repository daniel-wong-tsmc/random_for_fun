from __future__ import annotations
import argparse, json, pathlib, sys
from datetime import datetime, timezone
from gpu_agent.assignment import load_assignment
from gpu_agent.schema.finding import Finding, Confidence
from gpu_agent.schema.scorecard import DimensionRating
from gpu_agent.schema.raw_document import RawDocument
from gpu_agent.extraction.extractor import extract_findings
from gpu_agent.llm.recorded import RecordedClient
from gpu_agent.llm.factory import make_client
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

def _extract(args) -> int:
    docs = [RawDocument.model_validate(json.loads(p.read_text("utf-8")))
            for p in sorted(pathlib.Path(args.docs).glob("*.json"))]
    if args.recorded:
        client = RecordedClient(json.loads(pathlib.Path(args.recorded).read_text("utf-8")))
    else:
        client = make_client(args.backend)
    captured_at = args.captured_at or datetime.now(timezone.utc).isoformat()
    all_findings, all_dropped = [], []
    for doc in docs:
        outcome = extract_findings(doc, client, as_of=args.as_of, captured_at=captured_at,
                                   extraction_model=args.model, model=args.model)
        all_findings.extend(outcome.findings)
        all_dropped.extend(outcome.dropped)
    payload = json.dumps([f.model_dump() for f in all_findings], indent=2)
    if args.out:
        pathlib.Path(args.out).write_text(payload, encoding="utf-8")
        print(f"wrote {args.out}  {len(all_findings)} findings, {len(all_dropped)} dropped")
    else:
        print(payload)
    for d in all_dropped:
        print(f"DROPPED {d.id}: {'; '.join(d.violations)}", file=sys.stderr)
    return 0

def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="gpu-agent")
    sub = p.add_subparsers(dest="cmd", required=True)
    for name in ("run", "score"):           # ingest/extract/judge register in the adapter plan (spec §13.5)
        sp = sub.add_parser(name)
        sp.add_argument("--assignment", required=True)
        sp.add_argument("--fixtures", required=True, help="dir with findings.json, ratings.json, anchors.json")
        if name == "run":
            sp.add_argument("--out", default="store")
    ex = sub.add_parser("extract")
    ex.add_argument("--docs", required=True, help="dir of RawDocument JSON files")
    ex.add_argument("--as-of", required=True)
    ex.add_argument("--out", default=None)
    ex.add_argument("--model", default="claude-opus-4-8")
    ex.add_argument("--captured-at", default=None, help="ISO-8601; default: now (UTC)")
    ex.add_argument("--backend", default="claude_code")
    ex.add_argument("--recorded", default=None, help="JSON array of recorded responses (offline)")
    args = p.parse_args(argv)
    if args.cmd == "extract":
        return _extract(args)
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
