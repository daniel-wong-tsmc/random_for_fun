from __future__ import annotations
import argparse, json, pathlib, re, sys
from datetime import datetime, timezone
from pydantic import ValidationError
from gpu_agent.assignment import load_assignment
from gpu_agent.config import REGISTRY_PATH, TAXONOMY_PATH
from gpu_agent.schema.finding import Finding, Confidence
from gpu_agent.schema.scorecard import DimensionRating, CategoryStatus
from gpu_agent.schema.raw_document import RawDocument
from gpu_agent.extraction.extractor import extract_findings
from gpu_agent.extraction.extractor import ExtractionResult
from gpu_agent.extraction.prompt import (
    SYSTEM as EXTRACT_SYSTEM, build_system as build_extract_system,
    build_user_prompt as build_extract_user_prompt)
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
from gpu_agent.judgment.judge import JudgmentResult, JudgmentError
from gpu_agent.llm.client import LLMError
from gpu_agent.judgment.prompt import (
    SYSTEM as JUDGE_SYSTEM, build_system as build_judge_system,
    build_user_prompt as build_judge_user_prompt)
from gpu_agent.judgment.briefing import build_briefing
from gpu_agent.thesis import (
    ThesisAnswer, ThesisStore, apply_answer, gate_answer, seed_book,
    THESIS_SYSTEM, build_thesis_system, build_thesis_user_prompt)
from gpu_agent.memory import build_memory_bundle, render_memory_text
from gpu_agent.sufficiency import check_sufficiency
from gpu_agent.gathering.ingest import normalize_documents
from gpu_agent.gathering.dedup import (
    SeenDocIndex, filter_seen_documents, record_documents, classify_findings, DedupReport)
from gpu_agent.registry.indicators import IndicatorRegistry, RegistryError
from gpu_agent.registry.horizon import IndicatorHorizons
from gpu_agent.registry.structure import Taxonomy
from gpu_agent.registry.validate import validate_assignment
from gpu_agent.cycle import AssignmentProvider, CycleEntry, CyclePlan, build_cycle_plan
from gpu_agent.report import load_scorecard, find_prior, render_report
from gpu_agent.evals.cases import load_cases, CaseError
from gpu_agent.evals.harness import (
    BASELINE_SCHEMA_VERSION, build_grade_prompt, build_report, evaluate_v2,
    gate_brain_answer, load_baseline, rebaseline_v2, record_grades)
from gpu_agent.evals.prompt_hash import compute_prompt_hashes
from gpu_agent.asof import AsOfError
from gpu_agent.corpus import (
    SALIENCE_FLOOR_DEFAULT, CorpusError, assemble as corpus_assemble, render_coverage_text)

# F56-core: --as-of is embedded verbatim in doc/finding ids (F52), which become
# snapshot + FindingStore filenames -- a fat-fingered "2026/07/03" would mint a
# path-unsafe id. Validate the shape once at the CLI seam (defense-in-depth).
_AS_OF_RE = re.compile(r"^\d{4}-\d{2}(-\d{2})?$")
def _as_of(s: str) -> str:
    if not _AS_OF_RE.match(s):
        raise argparse.ArgumentTypeError(f"--as-of {s!r} must be YYYY-MM or YYYY-MM-DD")
    return s

def _load_docs(docs_dir: str) -> list[RawDocument]:
    return [RawDocument.model_validate(json.loads(p.read_text("utf-8")))
            for p in sorted(pathlib.Path(docs_dir).glob("*.json"))
            if p.name != "gather-log.json"]

def _load_registry():
    registry = IndicatorRegistry.load(REGISTRY_PATH)
    taxonomy = Taxonomy.load(TAXONOMY_PATH)
    registry.validate_against(taxonomy)
    return (registry, taxonomy)

def _gate_assignment(a, registry, taxonomy):
    violations = validate_assignment(a, registry, taxonomy)
    if violations:
        raise RegistryError(violations)

def _ingest(args) -> int:
    payload = json.loads(pathlib.Path(args.blobs).read_text("utf-8"))
    if isinstance(payload, list):
        blobs, rounds, skipped, pursued_despite_age = payload, 0, [], []
    else:
        blobs = payload.get("blobs", [])
        rounds = payload.get("rounds", 0)
        skipped = payload.get("skipped", [])
        pursued_despite_age = payload.get("pursuedDespiteAge", [])
    primary_sources = [s.strip() for s in args.primary_sources.split(",") if s.strip()]
    outcome = normalize_documents(blobs, primary_sources=primary_sources, as_of=args.as_of)
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
        "pursuedDespiteAge": pursued_despite_age,
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

def _corpus(args) -> int:
    """Handler for `gpu-agent corpus` (F62). Store-only mode (no --fresh) prints the
    coverage block for the gather top-up dispatch; assemble mode (--fresh) writes the
    merged corpus + deduped-fresh stream + CorpusReport. Every skip/drop is a stderr
    line AND a report field — nothing silent."""
    registry, _ = _load_registry()
    horizons = IndicatorHorizons.load(REGISTRY_PATH)
    fresh = []
    if args.fresh:
        if not args.out_merged:
            print("gpu-agent corpus: error: --fresh requires --out-merged", file=sys.stderr)
            return 2
        fresh = [Finding.model_validate(d)
                 for d in json.loads(pathlib.Path(args.fresh).read_text("utf-8"))]
    try:
        result = corpus_assemble(args.store, args.category, args.as_of, fresh,
                                 registry, horizons, salience_floor=args.salience_floor)
    except (CorpusError, AsOfError) as e:
        print(f"gpu-agent corpus: error: {e}", file=sys.stderr)
        return 1
    report = result.report
    for sp in report.skippedPages:
        print(f"SKIPPED-PAGE {sp.id}: category={sp.category}", file=sys.stderr)
    for sp in report.lifecycleExcluded:
        print(f"LIFECYCLE-EXCLUDED {sp.id}: pruned page", file=sys.stderr)
    for fc in report.freshDuplicate:
        print(f"DROPPED-DUPLICATE {fc.findingId}: {fc.detail or 'duplicate'}", file=sys.stderr)
    for fid in report.idOverlaps:
        print(f"ID-OVERLAP {fid}: store copy kept", file=sys.stderr)
    if report.fadedOut:
        print(f"faded-out: {report.fadedOut} store finding(s) below salience floor", file=sys.stderr)
    if args.report:
        pathlib.Path(args.report).write_text(report.model_dump_json(indent=2), "utf-8")
    if args.fresh:
        pathlib.Path(args.out_merged).write_text(
            json.dumps([f.model_dump() for f in result.merged], indent=2), "utf-8")
        if args.out_deduped_fresh:
            pathlib.Path(args.out_deduped_fresh).write_text(
                json.dumps([f.model_dump() for f in result.dedupedFresh], indent=2), "utf-8")
        print(f"store {len(report.storeIncluded)} aged ({report.fadedOut} faded), "
              f"fresh new {len(report.freshNew)} update {len(report.freshUpdate)} "
              f"duplicate {len(report.freshDuplicate)} -> merged {len(result.merged)}")
    else:
        print(render_coverage_text(report))
    return 0

def _wiki_lint(args) -> int:
    store = WikiStore(pathlib.Path(args.store) / "wiki",
                      FindingStore(pathlib.Path(args.store) / "findings"))
    registry, _ = _load_registry()
    horizons = IndicatorHorizons.load(REGISTRY_PATH)
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
    horizons = IndicatorHorizons.load(REGISTRY_PATH)
    # F32: the propose path is a READ — record=False so it neither logs nor mints a cycle.
    lint_report = lint(store, as_of=args.as_of, registry=registry, horizons=horizons,
                       record=False)
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
    horizons = IndicatorHorizons.load(REGISTRY_PATH)
    return build_scorecard(findings, ratings, anchors, a, narrative, confidence, registry,
                           category_status=category_status, horizons=horizons)

def _emit_extract_prompt(args) -> int:
    """Print the canonical extraction prompt + answer schema (no LLM call) so a Claude Code
    subagent can answer it; the answer feeds `extract --recorded`. Part 38: code emits the
    uniform prompt, the agent reasons, code gates the result."""
    docs = _load_docs(args.docs)
    persona = getattr(args, "persona", None)
    # F55: bake the taxonomy's impact.targets vocabulary into the emitted system prompt — the
    # same id set the gate enforces (taxonomy.categories) — so the dispatched brain never
    # depends on a coordinator-supplied id list. F53: same pattern for the price-side
    # indicator ids + canonical units the extractor seam now enforces. Completing F55: same
    # pattern again for the indicator id vocabulary the extractor's `unregistered indicator`
    # gate enforces (eval Task 10 finding) — ALL registered non-price ids, since the gate
    # accepts any registered id (structural and unsided included; price has its own list).
    registry, taxonomy = _load_registry()
    valid_targets = sorted(taxonomy.categories)
    scoring_indicators = [
        {"id": ind_id, "label": spec.label, "side": spec.side, "unit": spec.unit}
        for ind_id, spec in ((i, registry.resolve(i)) for i in sorted(registry.indicators))
        if spec.side != "price"
    ]
    price_indicators = [
        {"id": ind_id, "label": spec.label, "unit": spec.unit,
         "comparability": spec.comparability}
        for ind_id, spec in ((i, registry.resolve(i)) for i in sorted(registry.indicators))
        if spec.side == "price"
    ]
    kwargs = {"valid_targets": valid_targets, "scoring_indicators": scoring_indicators,
              "price_indicators": price_indicators}
    bundle = {
        "system": build_extract_system(persona, **kwargs) if persona
                  else build_extract_system(**kwargs),
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
    prompt is built from the GATED findings via the same build_briefing the frozen brain uses.

    F5: also threads prior-cycle MEMORY (scorecards/theses/wiki/price state) from `args.store`
    when a prior scorecard exists for this category strictly before this cycle's asOf (taken
    from the gated findings themselves, which all carry the current cycle's asOf) -- absent a
    prior, memory_text stays None and build_judge_user_prompt returns the byte-identical legacy
    (pre-memory) prompt."""
    findings = [Finding.model_validate(d)
                for d in json.loads(pathlib.Path(args.findings).read_text("utf-8"))]
    registry, _ = _load_registry()
    briefing = build_briefing(findings, registry, args.category)
    persona = getattr(args, "persona", None)
    memory_text = None
    if findings:
        horizons = IndicatorHorizons.load(REGISTRY_PATH)
        memory = build_memory_bundle(args.store, args.category, findings[0].asOf, registry, horizons)
        if memory is not None:
            memory_text = render_memory_text(memory)
    bundle = {
        "system": build_judge_system(persona) if persona else JUDGE_SYSTEM,
        "schema": JudgmentResult.model_json_schema(),
        # F55: include_groups appends the code-computed per-dimension citation groups (and the
        # six dimension names) so the brains see the exact vocabulary the conflict-check enforces.
        "user": build_judge_user_prompt(briefing, memory_text=memory_text,
                                        include_groups=True, include_dates=True),
        "samples": args.samples,
    }
    print(json.dumps(bundle, indent=2))
    return 0


def _voice_lint_samples(raw_answers: list) -> list[str]:
    """F67: analyst-voice lint over a batch of recorded JudgmentResult samples (each a JSON
    string -- RecordedClient's replay shape). Shared by `judge --recorded` and
    `pipeline --recorded-judge`: both replay the same brain-answer shape into judge_findings/
    build_scorecard, so both must gate brain-written prose BEFORE it reaches a scorecard or
    the lint is dead code in the live cycle (which never calls `judge --recorded` directly --
    see .claude/skills/run-cycle/SKILL.md). Returns violations only; callers decide how to
    report/exit so both call sites keep their own `voice-lint:` stderr framing.

    Final-review addition: each violation is prefixed with `sample {i+1}: ` (1-based,
    dispatch order) so a multi-sample failure (--samples 3+) tells the coordinating
    session WHICH recorded answer to re-dispatch, not just what the violation was."""
    from gpu_agent import reader
    from gpu_agent.schema.scorecard import DIMENSIONS
    violations: list[str] = []
    for i, raw in enumerate(raw_answers):
        sample = json.loads(raw)
        prefix = f"sample {i + 1}: "
        sample_violations: list[str] = []
        sample_violations += reader.lint_prose(sample.get("narrative", ""), "narrative",
                                               max_sentences=3)
        for dim, d in (sample.get("dimensions") or {}).items():
            sample_violations += reader.lint_prose(d.get("rationale", ""), f"{dim}.rationale",
                                                    max_sentences=2)
        cs = sample.get("categoryStatus") or {}
        sample_violations += reader.lint_prose(cs.get("reason", ""), "categoryStatus.reason")
        label = cs.get("constraintLabel")
        if label:
            if label in DIMENSIONS or "bottleneck" in label.lower():
                sample_violations.append("categoryStatus.constraintLabel: must name the concrete "
                                         "constraint, not a dimension")
            if len(label.split()) > 6:
                sample_violations.append("categoryStatus.constraintLabel: over 6 words")
        violations += [prefix + v for v in sample_violations]
    return violations


def _report_voice_violations(violations: list[str]) -> int:
    """Print every voice-lint violation (one `voice-lint: ` line each -- the run-cycle skill
    greps that prefix) and return the shared failure exit code. Extracted from the two
    `judge --recorded` / `pipeline --recorded-judge` call sites, which were otherwise
    identical four-line print+return-1 blocks."""
    for v in violations:
        print(f"voice-lint: {v}", file=sys.stderr)
    return 1


def _report_sufficiency_violations(violations: list[str]) -> int:
    """Print every F63 evidence-sufficiency violation (one `sufficiency: ` line each --
    the run-cycle skill greps that prefix, same re-dispatch loop as `voice-lint: `)
    and return the shared failure exit code."""
    for v in violations:
        print(f"sufficiency: {v}", file=sys.stderr)
    return 1


def _report_judgment_conflict(exc: Exception) -> int:
    """F71 §3: a clean, re-dispatchable exit for an anchor/aggregation conflict judge_findings
    could not resolve — analogous to _report_sufficiency_violations. A session hitting an
    anchor conflict under --recorded/--recorded-judge sees an `anchor: ` line to re-dispatch
    on (the run-cycle skill can grep the prefix), never an uncaught traceback. Two shapes:
    a JudgmentError carries the specific gate/anchor violations; an LLMError means the recorded
    answer deque emptied mid-resample before an anchor-legal rating was reached (the §3 trap)."""
    if isinstance(exc, JudgmentError):
        for v in exc.violations:
            print(f"anchor: {v}", file=sys.stderr)
    else:
        print(f"anchor: recorded judge exhausted before an anchor-legal rating was reached "
              f"— re-dispatch with a rating the measured anchor allows ({exc})", file=sys.stderr)
    return 1


def _judge(args) -> int:
    if args.emit_prompt:
        return _emit_judge_prompt(args)
    if args.out is None:
        print("gpu-agent judge: error: --out is required", file=sys.stderr)
        return 2
    findings = [Finding.model_validate(d)
                for d in json.loads(pathlib.Path(args.findings).read_text("utf-8"))]
    registry, _ = _load_registry()
    if args.recorded:
        answers = json.loads(pathlib.Path(args.recorded).read_text("utf-8"))
        if len(answers) != args.samples:
            print(f"gpu-agent judge: error: recorded answers ({len(answers)}) != samples ({args.samples})",
                  file=sys.stderr)
            return 2
        # F67: lint each recorded sample's brain-written prose BEFORE the gate/apply
        # (judge_findings below) so a violating recorded answer fails loud instead of
        # silently producing exec-facing copy that breaks the analyst-voice rules.
        if not args.no_voice_lint:
            violations = _voice_lint_samples(answers)
            if violations:
                return _report_voice_violations(violations)
        # F63: evidence-sufficiency gate — rating/bottleneck changes vs the SAME
        # prior-cycle MEMORY the emitted prompt carried need primary or >=N-publisher
        # citations. No prior scorecard -> memory is None -> inert. F75 (v1.4): the whole-run
        # --no-sufficiency bypass is REMOVED — the gate always runs; F71's anchor-forced
        # exemption handles the one deadlock the bypass used to cover, and the residual
        # re-dispatches (never a whole-run skip) before the unattended pilot.
        horizons = IndicatorHorizons.load(REGISTRY_PATH)
        memory = build_memory_bundle(args.store, args.category, findings[0].asOf,
                                     registry, horizons)
        # F71: pass the measured anchors so an anchor-FORCED rating move (prior rating made
        # illegal by the Part 7 bound) is exempt from the sufficiency gate.
        anchors = build_briefing(findings, registry, args.category).anchors
        violations = check_sufficiency(answers, memory, {f.id: f for f in findings},
                                       anchors=anchors, exemptions={})
        if violations:
            return _report_sufficiency_violations(violations)
        client = RecordedClient(answers)
    else:
        client = make_client(args.backend)
    try:
        bundle = judge_findings(findings, client, registry, args.category, samples=args.samples,
                                model=args.model, persona=getattr(args, "persona", None))
    except (JudgmentError, LLMError) as e:   # F71 §3: clean anchor-conflict exit, not a traceback
        return _report_judgment_conflict(e)
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

def _thesis(args) -> int:
    """Handler for `gpu-agent thesis`: emit the canonical thesis-book prompt (standing book +
    gated findings + prior-cycle MEMORY when available), or gate + apply a recorded answer.
    Mirrors extract/judge's emit->recorded pattern (F6/F7); this is the CLI grammar's final
    always-emit-then-recorded stage -- neither flag is a usage error, not a silent no-op.

    Steps (spec order):
      1. load findings, index by id.
      2. seed the thesis store if it doesn't exist yet (first run for this category).
      3. build the F4 memory bundle (None when no prior scorecard exists).
      4. --emit-prompt: print system/schema/user, exit 0.
      5. --recorded: parse -> gate -> apply -> write -> print per-thesis summary lines +
         proposal/promotion/retirement notes, exit 0; a parse or gate failure exits 1 and
         never calls store.write (the book stays byte-unchanged).
      6. neither flag: exit 2.
    """
    findings = [Finding.model_validate(d)
                for d in json.loads(pathlib.Path(args.findings).read_text("utf-8"))]
    findings_by_id = {f.id: f for f in findings}

    store = ThesisStore(pathlib.Path(args.store) / "theses" / args.category)
    if not store.exists():
        seed_path = args.seed or f"registry/theses.{args.category}.json"
        book = seed_book(seed_path, args.category, args.as_of)
        seeded_record = {
            "asOf": args.as_of, "event": "seeded", "thesisId": "",
            "detail": [e.model_dump() for e in book.entries],
            "note": f"seeded {len(book.entries)} theses",
        }
        store.write(book, [seeded_record])
        print(f"seeded {len(book.entries)} theses", file=sys.stderr)
    else:
        book = store.load()

    registry, _ = _load_registry()
    horizons = IndicatorHorizons.load(REGISTRY_PATH)
    memory = build_memory_bundle(args.store, args.category, args.as_of, registry, horizons)
    memory_text = render_memory_text(memory) if memory is not None else None

    if args.emit_prompt:
        persona = getattr(args, "persona", None)
        bundle = {
            "system": build_thesis_system(persona) if persona else THESIS_SYSTEM,
            "schema": ThesisAnswer.model_json_schema(),
            "user": build_thesis_user_prompt(book, findings, memory_text),
        }
        print(json.dumps(bundle, indent=2))
        return 0

    if args.recorded:
        try:
            answer = ThesisAnswer.model_validate_json(
                pathlib.Path(args.recorded).read_text("utf-8"))
        except ValidationError as e:
            print(f"gpu-agent thesis: error: invalid recorded answer: {e}", file=sys.stderr)
            return 1
        violations = gate_answer(answer, book, findings_by_id, registry)
        if violations:
            print("THESIS GATE FAILED:", *violations, sep="\n  ", file=sys.stderr)
            return 1
        history: list[dict] = []
        if store.history_path.exists():
            with store.history_path.open("r", encoding="utf-8") as f:
                history = [json.loads(line) for line in f if line.strip()]
        new_book, records, notes = apply_answer(
            book, answer, as_of=args.as_of, findings_by_id=findings_by_id, history=history)
        store.write(new_book, records)
        for record in records:
            if "verdict" in record:   # judgment records only; lifecycle records surface via notes
                print(f"{record['thesisId']}: {record['verdict']} "
                      f"applied={record['applied']} conviction={record['conviction']}")
        for note in notes:
            print(note)
        return 0

    print("gpu-agent thesis: error: exactly one of --emit-prompt or --recorded is required",
          file=sys.stderr)
    return 2

def _eval(args) -> int:
    """F6 eval harness driver. Emit/record cycle mirrors extract/judge/thesis; run-dir files
    (brain-prompts/brain-answers/brain-gates/grade-prompts/grade-answers/report.json) are the
    contract the run-eval skill scripts against."""
    if args.action == "verdict":
        if not args.runs or len(args.runs) > 2:
            print("gpu-agent eval: error: verdict needs --runs with 1 or 2 run dirs",
                  file=sys.stderr)
            return 2
        reports = []
        for d in args.runs:
            p = pathlib.Path(d) / "report.json"
            if not p.exists():
                print(f"gpu-agent eval: error: no report.json in {d}", file=sys.stderr)
                return 2
            reports.append(json.loads(p.read_text("utf-8")))
        baseline = load_baseline(args.baseline)
        if baseline is None or baseline.get("schemaVersion") != BASELINE_SCHEMA_VERSION:
            print("gpu-agent eval: error: verdict requires a schema-v2 baseline; "
                  "migrate via 'eval rebaseline --runs <d1> <d2> <d3>'", file=sys.stderr)
            return 2
        v = evaluate_v2(baseline, reports)
        v["runs"] = [str(d) for d in args.runs]
        v["promptHashes"] = reports[0].get("promptHashes", {})
        vp = pathlib.Path(args.runs[-1]) / "verdict.json"
        vp.write_text(json.dumps(v, indent=2, sort_keys=True), "utf-8")
        print(f"{v['decision'].upper()}  -> {vp}")
        for r in v["reasons"]:
            print(f"  - {r}")
        return 0 if v["pass"] else 1

    if args.action == "rebaseline":
        if not args.runs:
            print("gpu-agent eval: error: rebaseline needs --runs <d1> <d2> <d3> "
                  "(the v1 --out form is gone; see the run-eval skill)", file=sys.stderr)
            return 2
        try:
            cases = load_cases(pathlib.Path(args.cases))
        except CaseError as e:
            print(f"gpu-agent eval: case error: {e}", file=sys.stderr)
            return 1
        registry, taxonomy = _load_registry()
        hashes = compute_prompt_hashes(registry, taxonomy,
                                       pathlib.Path("fixtures/evals/hash-input.json"))
        verdict = None
        if args.verdict_path:
            verdict = json.loads(pathlib.Path(args.verdict_path).read_text("utf-8"))
        try:
            rebaseline_v2([pathlib.Path(d) for d in args.runs], args.baseline, hashes,
                          cases, verdict=verdict,
                          force_reason=args.reason if args.force else None,
                          human_review=args.human_review)
        except ValueError as e:
            print(f"gpu-agent eval: {e}", file=sys.stderr)
            return 1
        print(f"baseline written -> {args.baseline}")
        return 0

    if not args.out:
        print(f"gpu-agent eval: error: --out is required for {args.action}",
              file=sys.stderr)
        return 2
    out = pathlib.Path(args.out)

    if args.action == "record-grade" and not args.as_of:
        print("gpu-agent eval: error: --as-of is required for record-grade", file=sys.stderr)
        return 2

    try:
        cases = load_cases(pathlib.Path(args.cases))
    except CaseError as e:
        print(f"gpu-agent eval: case error: {e}", file=sys.stderr)
        return 1
    if not cases:
        print(f"gpu-agent eval: no cases in {args.cases}", file=sys.stderr)
        return 1
    registry, taxonomy = _load_registry()
    from gpu_agent.evals.emit import emit_brain_bundle
    out.mkdir(parents=True, exist_ok=True)

    if args.action == "emit-brain":
        prompts = {c.caseId: emit_brain_bundle(c.seam, c.seam_input(), registry, taxonomy)
                   for c in cases if c.kind == "positive"}
        (out / "brain-prompts.json").write_text(json.dumps(prompts, indent=2), "utf-8")
        print(f"emitted {len(prompts)} brain prompts -> {out / 'brain-prompts.json'}")
        return 0

    if args.action == "record-brain":
        ba = out / "brain-answers.json"
        if not ba.exists():
            print(f"gpu-agent eval: error: {ba} not found; "
                  "run emit-brain and dispatch the brains first", file=sys.stderr)
            return 2
        answers = json.loads(ba.read_text("utf-8"))
        gates, failed = {}, []
        for c in cases:
            if c.kind != "positive":
                continue
            if c.caseId not in answers:
                gates[c.caseId] = {"ok": False, "violations": ["missing brain answer"]}
                failed.append(c.caseId)
                continue
            g = gate_brain_answer(c.seam, c.seam_input(), answers[c.caseId], registry, taxonomy)
            gates[c.caseId] = g.model_dump()
            if not g.ok:
                failed.append(c.caseId)
        (out / "brain-gates.json").write_text(json.dumps(gates, indent=2), "utf-8")
        for cid in failed:
            print(f"BRAIN GATE FAILED {cid}:", *gates[cid]["violations"],
                  sep="\n  ", file=sys.stderr)
        print(f"gated {len(gates)} answers, {len(failed)} failed -> {out / 'brain-gates.json'}")
        return 1 if failed else 0

    if args.action == "emit-grade":
        answers = {}
        ba = out / "brain-answers.json"
        if ba.exists():
            answers = json.loads(ba.read_text("utf-8"))
        prompts, missing = {}, []
        for c in cases:
            text = c.recordedAnswer if c.kind == "negative" else answers.get(c.caseId)
            if text is None:
                missing.append(c.caseId)
                continue
            prompts[c.caseId] = build_grade_prompt(c, text, registry, taxonomy)
        if missing:
            print("gpu-agent eval: error: no fresh brain answer for: " + ", ".join(missing),
                  file=sys.stderr)
            return 1
        (out / "grade-prompts.json").write_text(json.dumps(prompts, indent=2), "utf-8")
        print(f"emitted {len(prompts)} grade prompts -> {out / 'grade-prompts.json'}")
        return 0

    if args.action == "record-grade":
        ga = out / "grade-answers.json"
        if not ga.exists():
            print(f"gpu-agent eval: error: {ga} not found; "
                  "run emit-grade and dispatch the graders first", file=sys.stderr)
            return 2
        grade_answers = json.loads(ga.read_text("utf-8"))
        grades, violations = record_grades(cases, grade_answers)
        if violations:
            for cid, v in violations.items():
                print(f"GRADE GATE FAILED {cid}:", *v, sep="\n  ", file=sys.stderr)
            return 1
        hashes = compute_prompt_hashes(registry, taxonomy,
                                       pathlib.Path("fixtures/evals/hash-input.json"))
        baseline = load_baseline(args.baseline)
        report = build_report(cases, grades, hashes, baseline, as_of=args.as_of)
        (out / "report.json").write_text(json.dumps(report, indent=2, sort_keys=True), "utf-8")
        v = report["verdict"]
        print(f"{v['decision'].upper()}  seams: " +
              "  ".join(f"{s}={m:.2f}" for s, m in sorted(report["seamMeans"].items())))
        for r in v["reasons"]:
            print(f"  - {r}")
        return 0 if v["pass"] else 1

    print(f"gpu-agent eval: unknown action '{args.action}'", file=sys.stderr)
    return 2

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
        judge_answers = json.loads(pathlib.Path(args.recorded_judge).read_text("utf-8"))
        # F67: the live cycle never calls `judge --recorded` directly -- it produces the
        # scorecard via this --recorded-judge path (see .claude/skills/run-cycle/SKILL.md),
        # so the analyst-voice lint has to gate here too, before judge_findings/build_scorecard
        # below, or the lint added in judge --recorded never runs in production.
        if not args.no_voice_lint:
            violations = _voice_lint_samples(judge_answers)
            if violations:
                return _report_voice_violations(violations)
        jdg_client = RecordedClient(judge_answers)
    else:
        jdg_client = make_client(args.backend)
    a = load_assignment(args.assignment)
    if a.asOf != args.as_of:
        print(f"note: assignment asOf {a.asOf} overridden by run asOf {args.as_of} (F50)",
              file=sys.stderr)
        a = a.model_copy(update={"asOf": args.as_of})
    registry, taxonomy = _load_registry()
    _gate_assignment(a, registry, taxonomy)
    # F62: merge the aged store corpus into the judged + scored findings. Same
    # deterministic assemble() the `corpus` command runs over the emit step's findings
    # file, so the emitted prompt's anchors/citation groups and the gate's match —
    # provided the session reused one --captured-at (run-cycle states this).
    if args.corpus_store:
        horizons = IndicatorHorizons.load(REGISTRY_PATH)
        try:
            cres = corpus_assemble(args.corpus_store, a.category, args.as_of, findings,
                                   registry, horizons, salience_floor=args.corpus_salience_floor)
        except (CorpusError, AsOfError) as e:
            print(f"gpu-agent pipeline: corpus error: {e}", file=sys.stderr)
            return 1
        findings = cres.merged
        rep = cres.report
        if args.corpus_report:
            pathlib.Path(args.corpus_report).write_text(rep.model_dump_json(indent=2), "utf-8")
        print(f"corpus: store {len(rep.storeIncluded)} aged ({rep.fadedOut} faded), "
              f"fresh new {len(rep.freshNew)} update {len(rep.freshUpdate)} "
              f"duplicate {len(rep.freshDuplicate)} -> merged {len(findings)}",
              file=sys.stderr)
    # F63: same sufficiency gate at the pipeline seam, placed here (after the F62 corpus
    # merge above) rather than right next to the voice-lint check: `registry` and the
    # MERGED `findings` -- the same findings_by_id the judge's citations resolve against
    # -- aren't available until this point. Memory comes from the F62 corpus store when
    # provided (the live cycle always passes --corpus-store); without it there is no
    # prior-state source here -> inert, matching the memory-less legacy pipeline.
    anchor_bounded: set[str] = set()   # F71: dims whose move was anchor-forced (trust-footer stamp)
    # F75 (v1.4): whole-run --no-sufficiency removed — the gate always runs on the recorded path.
    if args.recorded_judge:
        memory = None
        if args.corpus_store:
            horizons = IndicatorHorizons.load(REGISTRY_PATH)
            memory = build_memory_bundle(args.corpus_store, a.category, args.as_of,
                                         registry, horizons)
        # F71: measured anchors enable the anchor-forced-move exemption; exempted dims are
        # collected so build_scorecard can stamp them on the existing dimensionStatus note.
        anchors = build_briefing(findings, registry, a.category).anchors
        exemptions: dict[str, str] = {}
        violations = check_sufficiency(judge_answers, memory, {f.id: f for f in findings},
                                       anchors=anchors, exemptions=exemptions)
        if violations:
            return _report_sufficiency_violations(violations)
        anchor_bounded = set(exemptions)
    # F5: judge_findings' signature is frozen and builds its own prompt internally, so this
    # recorded-judge path threads no memory of its own -- the skill's live cycle gets prior-cycle
    # MEMORY via the `judge --emit-prompt --store ...` call in Step 3(c), whose emitted user
    # prompt is what the dispatched brain actually answers; --recorded-judge here just replays
    # that saved answer through the frozen gate/scorer.
    try:
        bundle = judge_findings(findings, jdg_client, registry, a.category, samples=args.samples,
                                model=args.model, persona=a.personaLabel)   # F26: assignment-driven persona
    except (JudgmentError, LLMError) as e:   # F71 §3: clean anchor-conflict exit, not a traceback
        return _report_judgment_conflict(e)
    horizons = IndicatorHorizons.load(REGISTRY_PATH)
    sc = build_scorecard(findings, bundle.ratings, bundle.anchors, a, bundle.narrative, bundle.confidence, registry,
                         category_status=bundle.categoryStatus, horizons=horizons,
                         anchor_bounded=frozenset(anchor_bounded))
    path = JsonStore(pathlib.Path(args.out)).append(sc)
    print(f"wrote {path}  DMI={sc.demandSupply.dmiContribution:.3f} "
          f"SMI={sc.demandSupply.smiContribution:.3f}")
    return 0

# F74 — a bare plan is regenerable; anything richer is a finalized run journal (or unknown
# content) and cycle-plan must never destroy it. Journals are session-authored at finalize.
# Key sets derive from the models so a schema change can never drift them out of sync.
_PLAN_TOP_KEYS = set(CyclePlan.model_fields)
_PLAN_ENTRY_KEYS = set(CycleEntry.model_fields)
_PLAN_STAGE_KEYS = {"tier", "status"}  # stages is list[dict[str,str]] — no model to derive from

def _is_bare_plan(payload) -> bool:
    if not isinstance(payload, dict) or set(payload) - _PLAN_TOP_KEYS:
        return False
    entries, stages = payload.get("entries"), payload.get("stages")
    if not isinstance(entries, list) or not isinstance(stages, list):
        return False   # null/absent/mis-typed containers are unrecognized content, not bare
    return (all(isinstance(e, dict) and not (set(e) - _PLAN_ENTRY_KEYS) for e in entries)
            and all(isinstance(s, dict) and not (set(s) - _PLAN_STAGE_KEYS) for s in stages))

def _cycle_plan(args) -> int:
    taxonomy = Taxonomy.load(args.taxonomy)
    provider = AssignmentProvider(args.assignments)
    plan = build_cycle_plan(args.scope, taxonomy, provider)   # raises ValueError on bad scope
    payload = plan.model_dump_json(indent=2)
    if args.out:
        out_path = pathlib.Path(args.out)
        if out_path.exists():
            try:
                # utf-8-sig: a BOM added by a Windows editor must not disguise a bare plan
                existing = json.loads(out_path.read_text(encoding="utf-8-sig"))
            except (OSError, json.JSONDecodeError, UnicodeDecodeError):
                existing = None      # unreadable/unparseable (or a directory): refuse below
            if not _is_bare_plan(existing):
                print(f"gpu-agent cycle-plan: error: refusing to overwrite {out_path} — it "
                      f"holds a finalized run journal (or unrecognized content), not a "
                      f"regenerable plan skeleton. Write the plan into the run's work/ dir; "
                      f"the canonical journal is session-authored at finalize (F74). If the "
                      f"target is known scratch (e.g. a truncated plan), delete it and re-run.",
                      file=sys.stderr)
                return 1
        out_path.write_text(payload, encoding="utf-8")
    print(payload)
    for e in plan.entries:
        if e.status != "ready":
            print(f"SKIPPED {e.category_id}: {e.status}", file=sys.stderr)
    return 0

def _latest_thesis_findings(history_path: pathlib.Path) -> dict:
    """Per-thesis findingIds from the LATEST history judgment record for each thesisId.

    Judgment records are the ones carrying a 'verdict' key (lifecycle records — seeded/
    proposed/promoted/retired/challenge-lapsed — do not and are skipped). history.jsonl
    is append-only chronological, so a plain forward scan that overwrites on every
    matching line naturally leaves the last (most recent) record per thesisId.
    """
    latest: dict = {}
    if not history_path.exists():
        return latest
    with history_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            record = json.loads(line)
            if "verdict" in record:
                latest[record["thesisId"]] = record["findingIds"]
    return latest


def _report(args) -> int:
    """Handler for `gpu-agent report`: load scorecard + optional prior → render."""
    try:
        sc = load_scorecard(pathlib.Path(args.scorecard))
    except (ValueError, FileNotFoundError) as e:
        print(f"gpu-agent report: error: {e}", file=sys.stderr)
        return 1

    # Task 4 (5-2 output surgery): THE CALLS / WHY are pure projections of the standing
    # thesis book. Absent store -> both stay None and brief.render_the_calls/render_why
    # degrade to their honest empty-state lines. A present-but-drifted book raises
    # ThesisStoreError, uncaught here -- fail loud, never silently trust a bad book
    # (mirrors the existing convention of not swallowing RegistryError in this handler).
    tstore = ThesisStore(pathlib.Path(args.store) / "theses" / sc.categoryId)
    thesis_book = None
    thesis_last_findings = None
    if tstore.exists():
        thesis_book = tstore.load()
        thesis_last_findings = _latest_thesis_findings(tstore.history_path)

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
    # F75: surface any bypassed/waived gate from the run's cycle log in the trust footer.
    from gpu_agent import brief
    gate_waivers: list[str] = []
    cycle_log = getattr(args, "cycle_log", None)
    if cycle_log:
        try:
            log = json.loads(pathlib.Path(cycle_log).read_text("utf-8"))
        except (OSError, json.JSONDecodeError) as e:
            print(f"gpu-agent report: warning: could not read cycle log {cycle_log}: {e}",
                  file=sys.stderr)
        else:
            entries = log.get("entries", []) if isinstance(log, dict) else []
            entry = next((e for e in entries
                          if isinstance(e, dict) and e.get("category_id") == sc.categoryId), None)
            gate_waivers = brief.gate_waivers_from_cycle_log((entry or {}).get("gates"))
    text = render_report(sc, prior, registry,
                         render_ts=getattr(args, "render_ts", None),
                         horizons=horizons, movement=movement,
                         thesis_book=thesis_book, thesis_last_findings=thesis_last_findings,
                         daily=getattr(args, "daily", False), gate_waivers=gate_waivers)
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


def _web_reach_ensure(args) -> int:
    from gpu_agent import web_reach_ensure as wre
    # Call with the module attribute (not the def-time default) so tests that
    # monkeypatch wre.REGISTRY_PATH are honored (see Task 2 review note).
    registry = wre.load_registry(wre.REGISTRY_PATH)
    log = (lambda m: None) if args.json else print
    results = wre.ensure_all(registry, check_only=args.check_only, timeout=args.timeout, log=log)
    if args.json:
        print(json.dumps({"webReach": {r["tool"]: r for r in results}}, indent=2))
    return 0 if all(r["status"] in ("ok", "installed-ok") for r in results) else 1


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
    ex.add_argument("--as-of", required=True, type=_as_of)
    ex.add_argument("--out", default=None)
    ex.add_argument("--model", default="claude-opus-4-8")
    ex.add_argument("--captured-at", default=None, help="ISO-8601; default: now (UTC)")
    ex.add_argument("--backend", default="claude_code")
    ex.add_argument("--recorded", default=None, help="JSON array of recorded responses (offline)")
    ex.add_argument("--persona", default=None,
                    help="analyst persona for the emitted system prompt (F26; default: GPU market)")
    ex.add_argument("--emit-prompt", action="store_true",
                    help="print the canonical extraction prompt + schema (no LLM) and exit")
    ig = sub.add_parser("ingest")
    ig.add_argument("--blobs", required=True, help="JSON: bare blob array or {rounds,skipped,blobs}")
    ig.add_argument("--out", required=True, help="dir for RawDocument JSON files + gather-log.json")
    ig.add_argument("--primary-sources", default="sec.gov",
                    help="comma-separated primary/official domains; the gather skill supplies "
                         "the per-category set from the manifest's primaryDomains (default is a "
                         "filings-only fallback)")
    ig.add_argument("--as-of", required=True, type=_as_of,
                    help="run vintage (YYYY-MM or YYYY-MM-DD); scopes document/finding ids (F52) and keys the L1 seen-index")
    ig.add_argument("--dedup-store", default=None,
                    help="store root for cross-run L1 seen-document dedup (holds seen_docs.jsonl)")
    wi = sub.add_parser("wiki-ingest")
    wi.add_argument("--findings", required=True, help="JSON array of gated Findings")
    wi.add_argument("--store", default="store", help="store root (holds wiki/ and findings/)")
    wi.add_argument("--as-of", required=True, type=_as_of)
    wi.add_argument("--category", default=None, help="category id for auto-created entity pages")
    wi.add_argument("--recorded", default=None, help="path to a recorded IngestResult JSON")
    wi.add_argument("--emit-prompt", action="store_true",
                    help="print the canonical ingest prompt + schema (no LLM) and exit")
    wd = sub.add_parser("wiki-dedup")
    wd.add_argument("--findings", required=True, help="JSON array of gated Findings (this cycle)")
    wd.add_argument("--store", default="store", help="store root (holds wiki/ and findings/)")
    wd.add_argument("--as-of", required=True, type=_as_of)
    wd.add_argument("--out-findings", default=None,
                    help="write the deduped NEW+UPDATE findings JSON here (for wiki-ingest)")
    wd.add_argument("--report", default=None, help="write the DedupReport JSON here (else stdout)")
    wl = sub.add_parser("wiki-lint")
    wl.add_argument("--store", default="store", help="store root (holds wiki/ and findings/)")
    wl.add_argument("--as-of", required=True, type=_as_of)
    wl.add_argument("--prev-as-of", default=None,
                    help="prior cycle asOf for the diff window (default: auto-derive from the log)")
    wl.add_argument("--out", default=None, help="write the LintReport JSON here")
    wlc = sub.add_parser("wiki-lifecycle")
    wlc.add_argument("--store", default="store", help="store root (holds wiki/ and findings/)")
    wlc.add_argument("--as-of", required=True, type=_as_of)
    wlc.add_argument("--apply", action="store_true",
                     help="apply the proposed promotions/prunes (else propose-only)")
    wlc.add_argument("--report", default=None, help="write the LifecycleReport JSON here")
    co = sub.add_parser("corpus")
    co.add_argument("--store", default="store", help="store root (holds wiki/ and findings/)")
    co.add_argument("--category", required=True, help="category id (scopes wiki pages)")
    co.add_argument("--as-of", required=True, help="run vintage (YYYY-MM or YYYY-MM-DD)")
    co.add_argument("--salience-floor", type=float, default=SALIENCE_FLOOR_DEFAULT,
                    help=f"aged-corpus decay cutoff (default {SALIENCE_FLOOR_DEFAULT})")
    co.add_argument("--fresh", default=None,
                    help="this cycle's gated findings JSON; enables assemble mode")
    co.add_argument("--out-merged", default=None,
                    help="write the merged corpus findings here (required with --fresh)")
    co.add_argument("--out-deduped-fresh", default=None,
                    help="write the deduped NEW+UPDATE fresh stream here (for wiki-ingest)")
    co.add_argument("--report", default=None, help="write the CorpusReport JSON here")
    jg = sub.add_parser("judge")
    jg.add_argument("--findings", required=True, help="JSON array of gated Findings")
    jg.add_argument("--out", default=None, help="dir for ratings/anchors/narrative.json")
    jg.add_argument("--samples", type=int, default=3)
    jg.add_argument("--model", default="claude-opus-4-8")
    jg.add_argument("--backend", default="claude_code")
    jg.add_argument("--recorded", default=None, help="JSON array of recorded judgment responses")
    jg.add_argument("--no-voice-lint", action="store_true",
                    help="skip the F67 analyst-voice lint (legacy recorded fixtures)")
    # F75 (v1.4): the whole-run --no-sufficiency bypass is removed — the evidence-sufficiency
    # gate always runs; F71's anchor-forced exemption covers its one sanctioned use.
    jg.add_argument("--category", required=True, help="indicator category id (e.g. chips.merchant-gpu)")
    jg.add_argument("--persona", default=None,
                    help="analyst persona for the judgment system prompt (F26; default: GPU market)")
    jg.add_argument("--emit-prompt", action="store_true",
                    help="print the canonical judgment prompt + schema (no LLM) and exit")
    jg.add_argument("--store", default="store",
                    help="store root for prior-cycle MEMORY threading (F5) in --emit-prompt; default: 'store'")
    th = sub.add_parser("thesis")
    th.add_argument("--findings", required=True, help="JSON array of gated Findings")
    th.add_argument("--store", default="store", help="store root (holds theses/<category>/)")
    th.add_argument("--category", required=True, help="indicator category id (e.g. chips.merchant-gpu)")
    th.add_argument("--as-of", required=True, type=_as_of)
    th.add_argument("--emit-prompt", action="store_true",
                    help="print the canonical thesis prompt + schema (no LLM) and exit")
    th.add_argument("--recorded", default=None, help="path to a recorded ThesisAnswer JSON")
    th.add_argument("--seed", default=None,
                    help="seed file path for a first run (default: registry/theses.<category>.json)")
    th.add_argument("--persona", default=None,
                    help="analyst persona for the emitted system prompt (default: GPU market)")
    ev = sub.add_parser("eval", help="F6 eval harness: golden-set emit/record + rebaseline")
    ev.add_argument("action", choices=["emit-brain", "record-brain", "emit-grade",
                                       "record-grade", "verdict", "rebaseline"])
    ev.add_argument("--cases", default="fixtures/evals/cases")
    ev.add_argument("--out", default="", help="run dir (required for emit-*/record-*)")
    ev.add_argument("--as-of", default="", help="required for record-grade (report provenance)")
    ev.add_argument("--baseline", default="fixtures/evals/baseline.json")
    ev.add_argument("--runs", nargs="+", default=None,
                    help="run dirs: 1-2 for verdict, exactly 3 for rebaseline")
    ev.add_argument("--verdict", dest="verdict_path", default="",
                    help="verdict.json proving the gate PASS (rebaseline governance)")
    ev.add_argument("--force", action="store_true")
    ev.add_argument("--reason", default="")
    ev.add_argument("--human-review", default="")
    pl = sub.add_parser("pipeline")
    pl.add_argument("--docs", required=True, help="dir of RawDocument JSON files")
    pl.add_argument("--assignment", required=True)
    pl.add_argument("--out", default="store")
    pl.add_argument("--as-of", required=True, type=_as_of)
    pl.add_argument("--samples", type=int, default=3)
    pl.add_argument("--model", default="claude-opus-4-8")
    pl.add_argument("--captured-at", default=None, help="ISO-8601; default: now (UTC)")
    pl.add_argument("--backend", default="claude_code")
    pl.add_argument("--recorded-extract", default=None)
    pl.add_argument("--recorded-judge", default=None)
    pl.add_argument("--no-voice-lint", action="store_true",
                    help="skip the F67 analyst-voice lint on --recorded-judge (legacy recorded fixtures)")
    # F75 (v1.4): the whole-run --no-sufficiency bypass is removed — the gate always runs.
    pl.add_argument("--corpus-store", default=None,
                    help="store root; when given, merge the aged store corpus (F62) "
                         "into the judged + scored findings")
    pl.add_argument("--corpus-salience-floor", type=float, default=SALIENCE_FLOOR_DEFAULT,
                    help=f"aged-corpus decay cutoff (default {SALIENCE_FLOOR_DEFAULT})")
    pl.add_argument("--corpus-report", default=None, help="write the CorpusReport JSON here")
    cp = sub.add_parser("cycle-plan")
    cp.add_argument("--scope", required=True,
                    help="category:<id> | layer:<id> | all")
    cp.add_argument("--assignments", default="fixtures",
                    help="dir of asg.<category>.json files")
    cp.add_argument("--taxonomy", default=TAXONOMY_PATH)
    cp.add_argument("--out", default=None, help="write the cycle plan JSON here (initial cycle log)")
    rp = sub.add_parser("report")
    rp.add_argument("--scorecard", required=True, help="path to the scorecard JSON file")
    rp.add_argument("--store", default="store",
                    help="store root dir for auto-discovery of prior (default: 'store')")
    rp.add_argument("--out", default=None, help="write report to file instead of stdout")
    rp.add_argument("--registry", default=REGISTRY_PATH,
                    help=f"indicator registry path (default: {REGISTRY_PATH!r})")
    rp.add_argument("--render-ts", default=None,
                    help="fix the report's render timestamp (ISO-8601) for byte-reproducible output; "
                         "default: current UTC time")
    rp.add_argument("--daily", action="store_true",
                    help="daily cadence: lead with WHAT MOVED instead of STATE OF THE MARKET "
                         "(F67 §4; same renderer/section order otherwise)")
    rp.add_argument("--cycle-log", default=None,
                    help="path to the run's cycle-log JSON; any gate the log records as "
                         "bypassed/waived (gates.*) surfaces a waiver line in the trust footer (F75)")
    # --prior and --no-prior are mutually exclusive: passing both is a usage error.
    grp = rp.add_mutually_exclusive_group()
    grp.add_argument("--prior", default=None, help="explicit path to prior-cycle scorecard")
    grp.add_argument("--no-prior", action="store_true",
                     help="suppress prior-cycle lookup; Δ columns show —")
    wre = sub.add_parser("web-reach-ensure",
                         help="idempotently ensure web-reach tools are installed")
    wre.add_argument("--check-only", action="store_true")
    wre.add_argument("--json", action="store_true")
    wre.add_argument("--timeout", type=int, default=600)
    args = p.parse_args(argv)
    if args.cmd == "ingest":
        return _ingest(args)
    if args.cmd == "wiki-ingest":
        return _wiki_ingest(args)
    if args.cmd == "wiki-dedup":
        return _wiki_dedup(args)
    if args.cmd == "corpus":
        try:
            return _corpus(args)
        except RegistryError as e:
            print("REGISTRY GATE FAILED:", *e.violations, sep="\n  ", file=sys.stderr)
            return 1
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
    if args.cmd == "thesis":
        try:
            return _thesis(args)
        except RegistryError as e:
            print("REGISTRY GATE FAILED:", *e.violations, sep="\n  ", file=sys.stderr)
            return 1
    if args.cmd == "eval":
        try:
            return _eval(args)
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
    if args.cmd == "web-reach-ensure":
        return _web_reach_ensure(args)
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
