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
from gpu_agent.judgment.judge import judge_findings
from gpu_agent.gathering.ingest import normalize_documents
from gpu_agent.registry.indicators import IndicatorRegistry, RegistryError
from gpu_agent.registry.structure import Taxonomy
from gpu_agent.registry.validate import validate_assignment
from gpu_agent.cycle import AssignmentProvider, build_cycle_plan

def _load_docs(docs_dir: str) -> list[RawDocument]:
    return [RawDocument.model_validate(json.loads(p.read_text("utf-8")))
            for p in sorted(pathlib.Path(docs_dir).glob("*.json"))
            if p.name != "gather-log.json"]

def _load_registry():
    registry = IndicatorRegistry.load("registry/indicators.json")
    taxonomy = Taxonomy.load("docs/taxonomy.json")
    registry.validate_against(taxonomy)
    return (registry, taxonomy)

def _gate_assignment(a, registry, taxonomy):
    violations = validate_assignment(a, registry, taxonomy)
    if violations:
        raise RegistryError(violations)

def _ingest(args) -> int:
    payload = json.loads(pathlib.Path(args.blobs).read_text("utf-8"))
    if isinstance(payload, list):
        blobs, rounds, skipped = payload, 0, []
    else:
        blobs = payload.get("blobs", [])
        rounds = payload.get("rounds", 0)
        skipped = payload.get("skipped", [])
    primary_sources = [s.strip() for s in args.primary_sources.split(",") if s.strip()]
    outcome = normalize_documents(blobs, primary_sources=primary_sources)
    out = pathlib.Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    for doc in outcome.documents:
        (out / f"{doc.id}.json").write_text(json.dumps(doc.model_dump(), indent=2), "utf-8")
    n_primary = sum(1 for d in outcome.documents if d.tier == "primary")
    log = {
        "rounds": rounds,
        "documents": len(outcome.documents),
        "primary": n_primary,
        "secondary": len(outcome.documents) - n_primary,
        "duplicates": outcome.duplicates,
        "dropped": [d.model_dump() for d in outcome.dropped],
        "skipped": skipped,
    }
    (out / "gather-log.json").write_text(json.dumps(log, indent=2), "utf-8")
    for d in outcome.dropped:
        print(f"DROPPED [{d.index}] {d.url}: {d.reason}", file=sys.stderr)
    print(f"ingested {len(outcome.documents)} docs "
          f"({outcome.duplicates} dup, {len(outcome.dropped)} dropped) -> {out}")
    return 0

def _build(args):
    a = load_assignment(args.assignment)
    fx = pathlib.Path(args.fixtures)
    findings = [Finding.model_validate(d) for d in json.loads((fx / "findings.json").read_text("utf-8"))]
    ratings = {k: DimensionRating.model_validate(v)
               for k, v in json.loads((fx / "ratings.json").read_text("utf-8")).items()}
    anchors = json.loads((fx / "anchors.json").read_text("utf-8"))
    narrative, confidence = "MVP scorecard.", Confidence(level="medium", basis="fixture run")
    npath = fx / "narrative.json"
    if npath.exists():
        nd = json.loads(npath.read_text("utf-8"))
        narrative = nd["narrative"]
        confidence = Confidence.model_validate(nd["confidence"])
    registry, _ = _load_registry()
    return build_scorecard(findings, ratings, anchors, a, narrative, confidence, registry)

def _extract(args) -> int:
    docs = _load_docs(args.docs)
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

def _judge(args) -> int:
    findings = [Finding.model_validate(d)
                for d in json.loads(pathlib.Path(args.findings).read_text("utf-8"))]
    if args.recorded:
        client = RecordedClient(json.loads(pathlib.Path(args.recorded).read_text("utf-8")))
    else:
        client = make_client(args.backend)
    registry, _ = _load_registry()
    bundle = judge_findings(findings, client, registry, args.category, samples=args.samples, model=args.model)
    out = pathlib.Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "ratings.json").write_text(
        json.dumps({k: v.model_dump() for k, v in bundle.ratings.items()}, indent=2), "utf-8")
    (out / "anchors.json").write_text(json.dumps(bundle.anchors, indent=2), "utf-8")
    (out / "narrative.json").write_text(
        json.dumps({"narrative": bundle.narrative, "confidence": bundle.confidence.model_dump()},
                   indent=2), "utf-8")
    print(f"judged {len(bundle.ratings)} dimensions -> {out}")
    return 0

def _pipeline(args) -> int:
    docs = _load_docs(args.docs)
    if args.recorded_extract:
        ext_client = RecordedClient(json.loads(pathlib.Path(args.recorded_extract).read_text("utf-8")))
    else:
        ext_client = make_client(args.backend)
    captured_at = args.captured_at or datetime.now(timezone.utc).isoformat()
    findings = []
    for doc in docs:
        findings.extend(extract_findings(doc, ext_client, as_of=args.as_of, captured_at=captured_at,
                                         extraction_model=args.model, model=args.model).findings)
    if args.recorded_judge:
        jdg_client = RecordedClient(json.loads(pathlib.Path(args.recorded_judge).read_text("utf-8")))
    else:
        jdg_client = make_client(args.backend)
    a = load_assignment(args.assignment)
    registry, taxonomy = _load_registry()
    _gate_assignment(a, registry, taxonomy)
    bundle = judge_findings(findings, jdg_client, registry, a.category, samples=args.samples, model=args.model)
    sc = build_scorecard(findings, bundle.ratings, bundle.anchors, a, bundle.narrative, bundle.confidence, registry)
    path = JsonStore(pathlib.Path(args.out)).append(sc)
    print(f"wrote {path}  DMI={sc.demandSupply.dmiContribution:.3f} "
          f"SMI={sc.demandSupply.smiContribution:.3f}")
    return 0

def _cycle_plan(args) -> int:
    taxonomy = Taxonomy.load(args.taxonomy)
    provider = AssignmentProvider(args.assignments)
    plan = build_cycle_plan(args.scope, taxonomy, provider)   # raises ValueError on bad scope
    payload = plan.model_dump_json(indent=2)
    if args.out:
        pathlib.Path(args.out).write_text(payload, encoding="utf-8")
    print(payload)
    for e in plan.entries:
        if e.status != "ready":
            print(f"SKIPPED {e.category_id}: {e.status}", file=sys.stderr)
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
    ig = sub.add_parser("ingest")
    ig.add_argument("--blobs", required=True, help="JSON: bare blob array or {rounds,skipped,blobs}")
    ig.add_argument("--out", required=True, help="dir for RawDocument JSON files + gather-log.json")
    ig.add_argument("--primary-sources", default="sec.gov",
                    help="comma-separated authoritative-source host allowlist")
    jg = sub.add_parser("judge")
    jg.add_argument("--findings", required=True, help="JSON array of gated Findings")
    jg.add_argument("--out", required=True, help="dir for ratings/anchors/narrative.json")
    jg.add_argument("--samples", type=int, default=3)
    jg.add_argument("--model", default="claude-opus-4-8")
    jg.add_argument("--backend", default="claude_code")
    jg.add_argument("--recorded", default=None, help="JSON array of recorded judgment responses")
    jg.add_argument("--category", default="chips.merchant-gpu", help="indicator category id")
    pl = sub.add_parser("pipeline")
    pl.add_argument("--docs", required=True, help="dir of RawDocument JSON files")
    pl.add_argument("--assignment", required=True)
    pl.add_argument("--out", default="store")
    pl.add_argument("--as-of", required=True)
    pl.add_argument("--samples", type=int, default=3)
    pl.add_argument("--model", default="claude-opus-4-8")
    pl.add_argument("--captured-at", default=None, help="ISO-8601; default: now (UTC)")
    pl.add_argument("--backend", default="claude_code")
    pl.add_argument("--recorded-extract", default=None)
    pl.add_argument("--recorded-judge", default=None)
    cp = sub.add_parser("cycle-plan")
    cp.add_argument("--scope", required=True,
                    help="category:<id> | layer:<id> | all")
    cp.add_argument("--assignments", default="fixtures",
                    help="dir of asg.<category>.json files")
    cp.add_argument("--taxonomy", default="docs/taxonomy.json")
    cp.add_argument("--out", default=None, help="write the cycle plan JSON here (initial cycle log)")
    args = p.parse_args(argv)
    if args.cmd == "ingest":
        return _ingest(args)
    if args.cmd == "extract":
        return _extract(args)
    if args.cmd == "judge":
        try:
            return _judge(args)
        except RegistryError as e:
            print("REGISTRY GATE FAILED:", *e.violations, sep="\n  ", file=sys.stderr)
            return 1
    if args.cmd == "pipeline":
        try:
            return _pipeline(args)
        except RegistryError as e:
            print("REGISTRY GATE FAILED:", *e.violations, sep="\n  ", file=sys.stderr)
            return 1
    if args.cmd == "cycle-plan":
        try:
            return _cycle_plan(args)
        except ValueError as e:
            print("CYCLE SCOPE ERROR:", e, file=sys.stderr)
            return 1
    try:
        sc = _build(args)
    except GateError as e:
        print("GATE FAILED:", *e.violations, sep="\n  ", file=sys.stderr)
        return 1
    except RegistryError as e:
        print("REGISTRY GATE FAILED:", *e.violations, sep="\n  ", file=sys.stderr)
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
