from __future__ import annotations
import argparse, json, pathlib, sys
from datetime import datetime, timezone
from gpu_agent.assignment import load_assignment
from gpu_agent.schema.finding import Finding, Confidence
from gpu_agent.schema.scorecard import DimensionRating, CategoryStatus
from gpu_agent.schema.raw_document import RawDocument
from gpu_agent.extraction.extractor import extract_findings
from gpu_agent.extraction.extractor import ExtractionResult
from gpu_agent.extraction.prompt import SYSTEM as EXTRACT_SYSTEM, build_user_prompt as build_extract_user_prompt
from gpu_agent.llm.recorded import RecordedClient
from gpu_agent.llm.factory import make_client
from gpu_agent.pipeline import build_scorecard
from gpu_agent.gate import GateError
from gpu_agent.store import JsonStore, FindingStore
from gpu_agent.wiki.store import WikiStore
from gpu_agent.wiki.ingest import route_findings, build_bundle, apply_enrichment, IngestResult
from gpu_agent.wiki.lint import lint
from gpu_agent.wiki.lifecycle import lifecycle, apply_lifecycle
from gpu_agent.wiki.movement import collect_movement
from gpu_agent.judgment.judge import judge_findings
from gpu_agent.judgment.judge import JudgmentResult
from gpu_agent.judgment.prompt import SYSTEM as JUDGE_SYSTEM, build_user_prompt as build_judge_user_prompt
from gpu_agent.judgment.briefing import build_briefing
from gpu_agent.gathering.ingest import normalize_documents
from gpu_agent.gathering.dedup import (
    SeenDocIndex, filter_seen_documents, record_documents, classify_findings, DedupReport)
from gpu_agent.registry.indicators import IndicatorRegistry, RegistryError
from gpu_agent.registry.horizon import IndicatorHorizons
from gpu_agent.registry.structure import Taxonomy
from gpu_agent.registry.validate import validate_assignment
from gpu_agent.cycle import AssignmentProvider, build_cycle_plan
from gpu_agent.report import load_scorecard, find_prior, render_report

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
    docs = outcome.documents
    dropped_known = []
    if getattr(args, "dedup_store", None):
        index = SeenDocIndex(pathlib.Path(args.dedup_store) / "seen_docs.jsonl")
        docs, dropped_known = filter_seen_documents(docs, index, as_of=args.as_of)
    out = pathlib.Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    for doc in docs:
        (out / f"{doc.id}.json").write_text(json.dumps(doc.model_dump(), indent=2), "utf-8")
    n_primary = sum(1 for d in docs if d.tier == "primary")
    log = {
        "rounds": rounds,
        "documents": len(docs),
        "primary": n_primary,
        "secondary": len(docs) - n_primary,
        "duplicates": outcome.duplicates,
        "dropped": [d.model_dump() for d in outcome.dropped],
        "skipped": skipped,
    }
    if getattr(args, "dedup_store", None):
        log["droppedKnown"] = len(dropped_known)
        log["droppedKnownDetail"] = [d.model_dump() for d in dropped_known]
    (out / "gather-log.json").write_text(json.dumps(log, indent=2), "utf-8")
    if getattr(args, "dedup_store", None):
        record_documents(docs, index, as_of=args.as_of)   # F12: only after snapshots are durable
    for d in outcome.dropped:
        print(f"DROPPED [{d.index}] {d.url}: {d.reason}", file=sys.stderr)
    for d in dropped_known:
        print(f"DROPPED-KNOWN {d.url}: {d.reason} (first seen {d.firstSeenAsOf})", file=sys.stderr)
    print(f"ingested {len(docs)} docs "
          f"({outcome.duplicates} dup, {len(outcome.dropped)} dropped, "
          f"{len(dropped_known)} known) -> {out}")
    return 0

def _wiki_ingest(args) -> int:
    findings = [Finding.model_validate(d)
                for d in json.loads(pathlib.Path(args.findings).read_text("utf-8"))]
    store = WikiStore(pathlib.Path(args.store) / "wiki",
                      FindingStore(pathlib.Path(args.store) / "findings"))
    touched = route_findings(store, findings, as_of=args.as_of, category=args.category)
    if args.emit_prompt:
        print(json.dumps(build_bundle(store, findings, touched, as_of=args.as_of), indent=2))
        return 0
    if args.recorded:
        result = IngestResult.model_validate_json(pathlib.Path(args.recorded).read_text("utf-8"))
        apply_enrichment(store, result, as_of=args.as_of)
        print(f"enriched {len(result.pages)} page(s) -> {args.store}")
        return 0
    print(f"routed {len(findings)} finding(s) to {len(touched)} page(s) -> {args.store}")
    return 0

def _wiki_dedup(args) -> int:
    findings = [Finding.model_validate(d)
                for d in json.loads(pathlib.Path(args.findings).read_text("utf-8"))]
    store = WikiStore(pathlib.Path(args.store) / "wiki",
                      FindingStore(pathlib.Path(args.store) / "findings"))
    result = classify_findings(findings, store)
    report = DedupReport(asOf=args.as_of, findingsNew=result.new,
                         findingsUpdate=result.update, findingsDuplicate=result.duplicate)
    if args.out_findings:
        # F10: outFindings carries the merged (corroboration/dispersion) representatives.
        # Fall back to the old id-filter only if outFindings is empty AND there are keeps —
        # no silent divergence between what's reported and what's written.
        keep = {fc.findingId for fc in result.new + result.update}
        if result.outFindings:
            deduped = [f.model_dump() for f in result.outFindings]
        elif keep:
            deduped = [f.model_dump() for f in findings if f.id in keep]
        else:
            deduped = []
        pathlib.Path(args.out_findings).write_text(json.dumps(deduped, indent=2), "utf-8")
    payload = report.model_dump_json(indent=2)
    if args.report:
        pathlib.Path(args.report).write_text(payload, "utf-8")
        print(f"wrote {args.report}  (new {len(result.new)}, update {len(result.update)}, "
              f"duplicate {len(result.duplicate)})")
    else:
        print(payload)
    return 0

def _wiki_lint(args) -> int:
    store = WikiStore(pathlib.Path(args.store) / "wiki",
                      FindingStore(pathlib.Path(args.store) / "findings"))
    registry, _ = _load_registry()
    horizons = IndicatorHorizons.load("registry/indicators.json")
    report = lint(store, as_of=args.as_of, prev_as_of=args.prev_as_of,
                  registry=registry, horizons=horizons)
    payload = report.model_dump_json(indent=2)
    if args.out:
        pathlib.Path(args.out).write_text(payload, encoding="utf-8")
        print(f"wrote {args.out}  ({len(report.material)} material, {len(report.dropped)} dropped)")
    else:
        print(payload)
    return 0


def _wiki_lifecycle(args) -> int:
    store = WikiStore(pathlib.Path(args.store) / "wiki",
                      FindingStore(pathlib.Path(args.store) / "findings"))
    registry, _ = _load_registry()
    horizons = IndicatorHorizons.load("registry/indicators.json")
    lint_report = lint(store, as_of=args.as_of, registry=registry, horizons=horizons)
    report = lifecycle(store, as_of=args.as_of, stale=lint_report.health.stale)
    payload = report.model_dump_json(indent=2)
    if args.report:
        pathlib.Path(args.report).write_text(payload, encoding="utf-8")
    if args.apply:
        summary = apply_lifecycle(store, report, as_of=args.as_of)
        print(f"applied: promoted {summary.promoted}, pruned {summary.pruned} -> {args.store}")
    else:
        print(payload)
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
    category_status = None
    spath = fx / "status.json"
    if spath.exists():
        category_status = CategoryStatus.model_validate_json(spath.read_text("utf-8"))
    registry, _ = _load_registry()
    horizons = IndicatorHorizons.load("registry/indicators.json")
    return build_scorecard(findings, ratings, anchors, a, narrative, confidence, registry,
                           category_status=category_status, horizons=horizons)

def _emit_extract_prompt(args) -> int:
    """Print the canonical extraction prompt + answer schema (no LLM call) so a Claude Code
    subagent can answer it; the answer feeds `extract --recorded`. Part 38: code emits the
    uniform prompt, the agent reasons, code gates the result."""
    docs = _load_docs(args.docs)
    bundle = {
        "system": EXTRACT_SYSTEM,
        "schema": ExtractionResult.model_json_schema(),
        "docs": [{"id": doc.id, "user": build_extract_user_prompt(doc)} for doc in docs],
    }
    print(json.dumps(bundle, indent=2))
    return 0

def _extract(args) -> int:
    if args.emit_prompt:
        return _emit_extract_prompt(args)
    docs = _load_docs(args.docs)
    if args.recorded:
        answers = json.loads(pathlib.Path(args.recorded).read_text("utf-8"))
        if len(answers) != len(docs):
            print(f"gpu-agent extract: error: recorded answers ({len(answers)}) != documents ({len(docs)})",
                  file=sys.stderr)
            return 2
        client = RecordedClient(answers)
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

def _emit_judge_prompt(args) -> int:
    """Print the canonical judgment prompt + answer schema (no LLM call) from the gated findings;
    the answer (a JSON array of `samples` JudgmentResults) feeds `judge --recorded`. The judgment
    prompt is built from the GATED findings via the same build_briefing the frozen brain uses."""
    findings = [Finding.model_validate(d)
                for d in json.loads(pathlib.Path(args.findings).read_text("utf-8"))]
    registry, _ = _load_registry()
    briefing = build_briefing(findings, registry, args.category)
    bundle = {
        "system": JUDGE_SYSTEM,
        "schema": JudgmentResult.model_json_schema(),
        "user": build_judge_user_prompt(briefing),
        "samples": args.samples,
    }
    print(json.dumps(bundle, indent=2))
    return 0


def _judge(args) -> int:
    if args.emit_prompt:
        return _emit_judge_prompt(args)
    if args.out is None:
        print("gpu-agent judge: error: --out is required", file=sys.stderr)
        return 2
    findings = [Finding.model_validate(d)
                for d in json.loads(pathlib.Path(args.findings).read_text("utf-8"))]
    if args.recorded:
        answers = json.loads(pathlib.Path(args.recorded).read_text("utf-8"))
        if len(answers) != args.samples:
            print(f"gpu-agent judge: error: recorded answers ({len(answers)}) != samples ({args.samples})",
                  file=sys.stderr)
            return 2
        client = RecordedClient(answers)
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
    if bundle.categoryStatus is not None:
        (out / "status.json").write_text(bundle.categoryStatus.model_dump_json(indent=2), "utf-8")
    print(f"judged {len(bundle.ratings)} dimensions -> {out}")
    return 0

def _pipeline(args) -> int:
    docs = _load_docs(args.docs)
    if args.recorded_extract:
        extract_answers = json.loads(pathlib.Path(args.recorded_extract).read_text("utf-8"))
        if len(extract_answers) != len(docs):
            print(f"gpu-agent pipeline: error: recorded answers ({len(extract_answers)}) "
                  f"!= documents ({len(docs)})", file=sys.stderr)
            return 2
        ext_client = RecordedClient(extract_answers)
    else:
        ext_client = make_client(args.backend)
    captured_at = args.captured_at or datetime.now(timezone.utc).isoformat()
    findings, dropped = [], []
    for doc in docs:
        outcome = extract_findings(doc, ext_client, as_of=args.as_of, captured_at=captured_at,
                                   extraction_model=args.model, model=args.model)
        findings.extend(outcome.findings)
        dropped.extend(outcome.dropped)
    for d in dropped:
        print(f"DROPPED {d.id}: {'; '.join(d.violations)}", file=sys.stderr)
    if dropped:
        print(f"gate dropped {len(dropped)} finding(s)", file=sys.stderr)
    if args.recorded_judge:
        jdg_client = RecordedClient(json.loads(pathlib.Path(args.recorded_judge).read_text("utf-8")))
    else:
        jdg_client = make_client(args.backend)
    a = load_assignment(args.assignment)
    registry, taxonomy = _load_registry()
    _gate_assignment(a, registry, taxonomy)
    bundle = judge_findings(findings, jdg_client, registry, a.category, samples=args.samples, model=args.model)
    horizons = IndicatorHorizons.load("registry/indicators.json")
    sc = build_scorecard(findings, bundle.ratings, bundle.anchors, a, bundle.narrative, bundle.confidence, registry,
                         category_status=bundle.categoryStatus, horizons=horizons)
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

def _report(args) -> int:
    """Handler for `gpu-agent report`: load scorecard + optional prior → render."""
    try:
        sc = load_scorecard(pathlib.Path(args.scorecard))
    except (ValueError, FileNotFoundError) as e:
        print(f"gpu-agent report: error: {e}", file=sys.stderr)
        return 1

    prior = None
    if not args.no_prior:
        if args.prior:
            # Explicit prior path supplied — load it directly.
            try:
                prior = load_scorecard(pathlib.Path(args.prior))
            except (ValueError, FileNotFoundError) as e:
                print(
                    f"gpu-agent report: warning: could not load prior: {e}",
                    file=sys.stderr,
                )
        else:
            # Auto-discover: pass current_path so find_prior excludes the
            # current scorecard by (asOf, version) and picks the highest
            # version strictly below it.  This is correct even when the
            # current scorecard is not the newest file in the store.
            unmatched: list[str] = []
            prior_path = find_prior(
                pathlib.Path(args.store), sc,
                current_path=pathlib.Path(args.scorecard),
                unmatched=unmatched,
            )
            for name in unmatched:
                print(f"gpu-agent report: note: ignoring non-scorecard file {name}", file=sys.stderr)
            if prior_path is not None:
                try:
                    prior = load_scorecard(prior_path)
                except (ValueError, FileNotFoundError) as e:
                    print(
                        f"gpu-agent report: warning: could not load prior {prior_path}: {e}",
                        file=sys.stderr,
                    )

    registry = IndicatorRegistry.load(args.registry)
    horizons = IndicatorHorizons.load(args.registry)   # same file; carries the cadenceHorizon tags
    wiki_dir = pathlib.Path(args.store) / "wiki"
    movement = None
    if wiki_dir.exists():
        store = WikiStore(wiki_dir, FindingStore(pathlib.Path(args.store) / "findings"))
        prev_as_of = prior.asOf if prior is not None else None
        movement = collect_movement(store, as_of=sc.asOf, prev_as_of=prev_as_of,
                                    registry=registry, horizons=horizons)
    text = render_report(sc, prior, registry,
                         render_ts=getattr(args, "render_ts", None),
                         horizons=horizons, movement=movement)
    # The report emits non-ASCII glyphs (↑↓→ — Δ). A default Windows cp1252
    # terminal would crash on print(); force stdout to UTF-8 so the CLI runs
    # on the user's own platform (covers both the report and the "wrote" line).
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if args.out:
        pathlib.Path(args.out).write_text(text, "utf-8")
        print(f"wrote {args.out}")
    else:
        print(text)
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
    ex.add_argument("--emit-prompt", action="store_true",
                    help="print the canonical extraction prompt + schema (no LLM) and exit")
    ig = sub.add_parser("ingest")
    ig.add_argument("--blobs", required=True, help="JSON: bare blob array or {rounds,skipped,blobs}")
    ig.add_argument("--out", required=True, help="dir for RawDocument JSON files + gather-log.json")
    ig.add_argument("--primary-sources", default="sec.gov",
                    help="comma-separated authoritative-source host allowlist")
    ig.add_argument("--as-of", default="",
                    help="cycle asOf stamped as first-seen in the L1 dedup index")
    ig.add_argument("--dedup-store", default=None,
                    help="store root for cross-run L1 seen-document dedup (holds seen_docs.jsonl)")
    wi = sub.add_parser("wiki-ingest")
    wi.add_argument("--findings", required=True, help="JSON array of gated Findings")
    wi.add_argument("--store", default="store", help="store root (holds wiki/ and findings/)")
    wi.add_argument("--as-of", required=True)
    wi.add_argument("--category", default=None, help="category id for auto-created entity pages")
    wi.add_argument("--recorded", default=None, help="path to a recorded IngestResult JSON")
    wi.add_argument("--emit-prompt", action="store_true",
                    help="print the canonical ingest prompt + schema (no LLM) and exit")
    wd = sub.add_parser("wiki-dedup")
    wd.add_argument("--findings", required=True, help="JSON array of gated Findings (this cycle)")
    wd.add_argument("--store", default="store", help="store root (holds wiki/ and findings/)")
    wd.add_argument("--as-of", required=True)
    wd.add_argument("--out-findings", default=None,
                    help="write the deduped NEW+UPDATE findings JSON here (for wiki-ingest)")
    wd.add_argument("--report", default=None, help="write the DedupReport JSON here (else stdout)")
    wl = sub.add_parser("wiki-lint")
    wl.add_argument("--store", default="store", help="store root (holds wiki/ and findings/)")
    wl.add_argument("--as-of", required=True)
    wl.add_argument("--prev-as-of", default=None,
                    help="prior cycle asOf for the diff window (default: auto-derive from the log)")
    wl.add_argument("--out", default=None, help="write the LintReport JSON here")
    wlc = sub.add_parser("wiki-lifecycle")
    wlc.add_argument("--store", default="store", help="store root (holds wiki/ and findings/)")
    wlc.add_argument("--as-of", required=True)
    wlc.add_argument("--apply", action="store_true",
                     help="apply the proposed promotions/prunes (else propose-only)")
    wlc.add_argument("--report", default=None, help="write the LifecycleReport JSON here")
    jg = sub.add_parser("judge")
    jg.add_argument("--findings", required=True, help="JSON array of gated Findings")
    jg.add_argument("--out", default=None, help="dir for ratings/anchors/narrative.json")
    jg.add_argument("--samples", type=int, default=3)
    jg.add_argument("--model", default="claude-opus-4-8")
    jg.add_argument("--backend", default="claude_code")
    jg.add_argument("--recorded", default=None, help="JSON array of recorded judgment responses")
    jg.add_argument("--category", default="chips.merchant-gpu", help="indicator category id")
    jg.add_argument("--emit-prompt", action="store_true",
                    help="print the canonical judgment prompt + schema (no LLM) and exit")
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
    rp = sub.add_parser("report")
    rp.add_argument("--scorecard", required=True, help="path to the scorecard JSON file")
    rp.add_argument("--store", default="store",
                    help="store root dir for auto-discovery of prior (default: 'store')")
    rp.add_argument("--out", default=None, help="write report to file instead of stdout")
    rp.add_argument("--registry", default="registry/indicators.json",
                    help="indicator registry path (default: 'registry/indicators.json')")
    rp.add_argument("--render-ts", default=None,
                    help="fix the report's render timestamp (ISO-8601) for byte-reproducible output; "
                         "default: current UTC time")
    # --prior and --no-prior are mutually exclusive: passing both is a usage error.
    grp = rp.add_mutually_exclusive_group()
    grp.add_argument("--prior", default=None, help="explicit path to prior-cycle scorecard")
    grp.add_argument("--no-prior", action="store_true",
                     help="suppress prior-cycle lookup; Δ columns show —")
    args = p.parse_args(argv)
    if args.cmd == "ingest":
        return _ingest(args)
    if args.cmd == "wiki-ingest":
        return _wiki_ingest(args)
    if args.cmd == "wiki-dedup":
        return _wiki_dedup(args)
    if args.cmd == "wiki-lint":
        return _wiki_lint(args)
    if args.cmd == "wiki-lifecycle":
        return _wiki_lifecycle(args)
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
    if args.cmd == "report":
        return _report(args)
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
