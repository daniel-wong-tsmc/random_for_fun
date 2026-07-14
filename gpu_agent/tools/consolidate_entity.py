"""F24 stage 2 Part B - one-shot historical consolidation of a split entity page
(spec docs/superpowers/specs/2026-07-13-f24-stage2-design.md).

Merges the OLD split page's observation history into the CANONICAL page as new
APPEND-ONLY wiki-log events, provenance-labeled via the event detail
("consolidation: moved from <old>"). The log is never rewritten - the old page's
original events stay in place; the canonical page gains new events carrying each
observation's ORIGINAL asOf vintage. The merged page state resolves by
latest-vintage-wins (asOf label order, the desk's event-order convention); the
losing value is preserved verbatim in the consolidation summary event body. Two
pages carrying contradictory states at the SAME vintage cannot be ordered by the
rule - that raises ConsolidationConflict with both shown (the spec's
QUESTION-STOP) and nothing is written. The old page is then retired: pointer body
naming the canonical page, symmetric crossRefs, and a prune-shaped state-change
(salience floored to the lifecycle prune floor, mirroring
lifecycle.apply_lifecycle's non-destructive prune) so corpus/lint stop
double-counting it without special-casing (corpus._is_pruned keys on exactly this
shape; "archived/retired are not wiki-page states in the current model").

Deterministic and replayable: no wall-clock (asOf comes from the caller),
plan-first (all reads and every integrity/conflict check happen BEFORE the first
write; a conflict aborts with nothing written), and idempotent (a second run with
the same arguments writes nothing - byte-identical store).

Uses only existing public store APIs (WikiStore methods + WikiLog.append, the same
direct-append surface wiki.lint already uses; FindingStore.exists). gpu_agent/wiki
internals are untouched. The one non-store kind used for the summary event is
"header-change" - non-material by design (lint.quiet_age ignores it), and the
retire IS a header-visible edit. Tests run against synthetic fixtures only;
running this against the live store and committing the result is a USER-SIGNED
step (spec Part B).
"""
from __future__ import annotations
import argparse
import difflib
import pathlib
import sys
from typing import Optional

from pydantic import BaseModel, Field

from gpu_agent.store import FindingStore
from gpu_agent.wiki.lifecycle import DEFAULT_LIFECYCLE_CONFIG
from gpu_agent.wiki.log import StateChange
from gpu_agent.wiki.store import WikiStore


class ConsolidationError(ValueError):
    """Integrity failure (missing page / dangling finding) - fail loud, nothing written."""


class ConsolidationConflict(ConsolidationError):
    """The two pages carry contradictory states the latest-vintage-wins rule cannot
    order (same asOf vintage, different values) - the spec's QUESTION-STOP trigger.
    Raised during planning; nothing has been written."""


def retire_state(new_id: str) -> str:
    """The old page's post-consolidation state string: self-describing pointer that
    shows up verbatim in the wiki index one-liner."""
    return f"retired -> {new_id}"


def pointer_body(old_id: str, new_id: str, as_of: str) -> str:
    return (
        f"RETIRED ({as_of}): consolidated into {new_id}.\n"
        f"\n"
        f"This page's observation history was merged into the canonical page as\n"
        f"append-only log events labeled \"consolidation: moved from {old_id}\".\n"
        f"Do not append new observations here - the canonical page is {new_id}.\n"
    )


def _fmt_record(page_id: str, sc: StateChange) -> str:
    return (f"{page_id} @ {sc.asOf}: state={sc.state!r} trajectory={sc.trajectory!r} "
            f"salience={sc.salience:g}")


class MovedObservation(BaseModel):
    findingId: str
    asOf: str                        # the observation's ORIGINAL vintage, preserved


class StateMergeResult(BaseModel):
    rule: str = "latest-vintage-wins"
    action: str                      # "apply-old" | "keep-canonical" | "already-equal"
    winner: str                      # _fmt_record of the winning record
    losing: Optional[str] = None     # the losing record - also preserved in the summary event


class ConsolidationReport(BaseModel):
    oldPageId: str
    newPageId: str
    asOf: str
    moved: list[MovedObservation] = Field(default_factory=list)
    alreadyPresent: list[str] = Field(default_factory=list)   # observed by both pages
    stateMerge: Optional[StateMergeResult] = None  # None: old page has no organic state history
    crossRefsAdded: list[str] = Field(default_factory=list)
    retired: bool = False            # the retire state-change was written THIS run
    pointerBodySet: bool = False
    changed: bool = False
    summaryDetail: str = ""


def consolidate(store: WikiStore, old_id: str, new_id: str, *, as_of: str) -> ConsolidationReport:
    """Merge `old_id`'s history into `new_id` and retire `old_id`. Plan-first: every
    integrity/conflict check happens before the first write. Idempotent: a second run
    with the same arguments returns changed=False and writes nothing."""
    if old_id == new_id:
        raise ConsolidationError(f"old and canonical page are the same: {old_id}")
    old_page = store.get_page(old_id)      # PageNotFound propagates - fail loud
    new_page = store.get_page(new_id)

    # ---------------- plan (pure reads) ----------------
    marker = retire_state(new_id)

    # 1. observations to move: old-page observations the canonical page lacks, first
    #    occurrence per finding id, original asOf preserved. Dangling refs fail loud.
    present = {o.findingId for o in store.observations(new_id)}
    to_move: list[MovedObservation] = []
    planned = set()
    already: list[str] = []
    for o in store.observations(old_id):
        if o.findingId in present:
            if o.findingId not in already:
                already.append(o.findingId)
            continue
        if o.findingId in planned:
            continue
        if not store.findings.exists(o.findingId):
            raise ConsolidationError(
                f"store integrity: {old_id} observes missing finding {o.findingId}")
        to_move.append(MovedObservation(findingId=o.findingId, asOf=o.asOf))
        planned.add(o.findingId)

    # 2. merged page state: latest-vintage-wins over each page's LATEST state record
    #    (a page's current state is its last state-change by (asOf, seq) - store
    #    convention). The old page's retire marker (a previous run's) is not organic
    #    state and is excluded. Full record (state/trajectory/salience) moves as one.
    old_hist = [s for s in store.state_history(old_id) if s.state != marker]
    new_hist = store.state_history(new_id)
    old_latest = old_hist[-1] if old_hist else None
    new_latest = new_hist[-1] if new_hist else None
    merge: Optional[StateMergeResult] = None
    apply_state: Optional[StateChange] = None
    if old_latest is not None:
        if new_latest is None:
            merge = StateMergeResult(action="apply-old",
                                     winner=_fmt_record(old_id, old_latest))
            apply_state = old_latest
        elif old_latest.asOf == new_latest.asOf:
            same = (old_latest.state == new_latest.state
                    and old_latest.trajectory == new_latest.trajectory
                    and old_latest.salience == new_latest.salience)
            if same:
                merge = StateMergeResult(action="already-equal",
                                         winner=_fmt_record(new_id, new_latest))
            else:
                raise ConsolidationConflict(
                    "contradictory page states at the SAME vintage - "
                    "latest-vintage-wins cannot order them (QUESTION-STOP, spec Part B):\n"
                    f"  old:       {_fmt_record(old_id, old_latest)}\n"
                    f"  canonical: {_fmt_record(new_id, new_latest)}")
        elif old_latest.asOf > new_latest.asOf:
            merge = StateMergeResult(action="apply-old",
                                     winner=_fmt_record(old_id, old_latest),
                                     losing=_fmt_record(new_id, new_latest))
            apply_state = old_latest
        else:
            merge = StateMergeResult(action="keep-canonical",
                                     winner=_fmt_record(new_id, new_latest),
                                     losing=_fmt_record(old_id, old_latest))

    # 3. retire-pointer plan: symmetric crossRefs, prune-shaped state, pointer body.
    add_new_ref = old_id not in new_page.crossRefs
    add_old_ref = new_id not in old_page.crossRefs
    floor = DEFAULT_LIFECYCLE_CONFIG.prune_salience_floor
    need_retire = not (old_page.state == marker
                       and old_page.salience <= floor
                       and bool(store.state_history(old_id)))
    body = pointer_body(old_id, new_id, as_of)
    need_body = store.window(old_id, 0).body != body

    changed = bool(to_move) or apply_state is not None or add_new_ref or add_old_ref \
        or need_retire or need_body

    parts = [f"consolidation: merged {old_id} into {new_id}",
             f"moved {len(to_move)} observation(s)"
             + (f" [{', '.join(m.findingId for m in to_move)}]" if to_move else "")]
    if already:
        parts.append(f"{len(already)} already on canonical [{', '.join(already)}]")
    if merge is None:
        parts.append("state-merge: none (old page has no organic state history)")
    else:
        s = f"state-merge {merge.rule}: {merge.action}; winner {merge.winner}"
        if merge.losing:
            s += f"; losing value preserved: {merge.losing}"
        parts.append(s)
    parts.append(f"retired {old_id} (pointer body -> {new_id})")
    detail = "; ".join(parts)

    report = ConsolidationReport(
        oldPageId=old_id, newPageId=new_id, asOf=as_of,
        moved=to_move, alreadyPresent=already, stateMerge=merge,
        crossRefsAdded=([f"{new_id} -> {old_id}"] if add_new_ref else [])
        + ([f"{old_id} -> {new_id}"] if add_old_ref else []),
        retired=need_retire, pointerBodySet=need_body, changed=changed,
        summaryDetail=detail if changed else "")

    # ---------------- apply (writes; skipped entirely when nothing changed) ----------------
    if not changed:
        return report
    for m in to_move:
        store.log.append(asOf=m.asOf, kind="append-observation", pageId=new_id,
                         findingId=m.findingId,
                         detail=f"consolidation: moved from {old_id}")
    if apply_state is not None:
        store.record_state(new_id, as_of=apply_state.asOf, state=apply_state.state,
                           trajectory=apply_state.trajectory,
                           salience=apply_state.salience,
                           finding_id=apply_state.findingId)
    if add_new_ref:
        store.update_header(new_id, as_of=as_of, crossRefs=[*new_page.crossRefs, old_id])
    if add_old_ref:
        store.update_header(old_id, as_of=as_of, crossRefs=[*old_page.crossRefs, new_id])
    if need_retire:
        store.record_state(old_id, as_of=as_of, state=marker,
                           trajectory=f"consolidated into {new_id}", salience=floor)
    store.set_body(old_id, body, as_of=as_of)   # idempotent: no-op on identical body
    # The summary/provenance event: non-material kind (quiet_age ignores header-change),
    # carries the rule application and any LOSING value in its body per the spec.
    store.log.append(asOf=as_of, kind="header-change", pageId=old_id, detail=detail)
    return report


# ---------------- CLI: snapshot -> consolidate -> full before/after diff artifact ----------------

def _page_path(store_root: pathlib.Path, page_id: str) -> pathlib.Path:
    ptype, _, slug = page_id.partition(":")
    return store_root / "wiki" / ptype / f"{slug}.md"


def _snapshot(store_root: pathlib.Path, page_ids) -> dict:
    pages = {}
    for pid in page_ids:
        p = _page_path(store_root, pid)
        pages[pid] = p.read_text(encoding="utf-8") if p.exists() else ""
    log_path = store_root / "wiki" / "log.jsonl"
    return {"pages": pages,
            "log": log_path.read_text(encoding="utf-8") if log_path.exists() else ""}


def _shape(store: WikiStore, pid: str) -> dict:
    page = store.get_page(pid)
    hist = store.state_history(pid)
    return {"observations": len(store.observations(pid)),
            "stateChanges": len(hist),
            "state": page.state, "salience": page.salience,
            "crossRefs": list(page.crossRefs),
            "pruneShaped": page.salience <= DEFAULT_LIFECYCLE_CONFIG.prune_salience_floor
            and bool(hist)}


def _fenced(kind: str, text: str) -> list[str]:
    return [f"```{kind}", *text.rstrip("\n").split("\n"), "```", ""]


def write_diff_artifact(out_path: pathlib.Path, *, old_id, new_id, as_of, store_root,
                        before, after, shapes_before, shapes_after,
                        report: ConsolidationReport) -> None:
    """The FULL before/after diff artifact for the user's sign-off: unified diffs,
    complete page files before and after, every appended log line, page shapes."""
    lines = [f"# Entity consolidation diff: {old_id} -> {new_id}", "",
             f"- asOf: {as_of}",
             f"- store root: {store_root}",
             f"- changed: {report.changed}", "",
             "## Report", ""]
    lines += _fenced("json", report.model_dump_json(indent=2))
    lines += ["## Page shapes (before -> after)", ""]
    for pid in (old_id, new_id):
        lines.append(f"- `{pid}`: {shapes_before[pid]}")
        lines.append(f"  -> {shapes_after[pid]}")
    lines.append("")
    for pid in (old_id, new_id):
        diff = list(difflib.unified_diff(
            before["pages"][pid].splitlines(), after["pages"][pid].splitlines(),
            fromfile=f"before/{pid}", tofile=f"after/{pid}", lineterm=""))
        lines += [f"## Unified diff: {pid}", ""]
        lines += _fenced("diff", "\n".join(diff) if diff else "(no change)")
    n_before = len(before["log"].splitlines())
    n_after = len(after["log"].splitlines())
    appended = after["log"].splitlines()[n_before:]
    lines += [f"## Wiki log: appended events ({n_before} -> {n_after} lines; append-only)", ""]
    lines += _fenced("", "\n".join(appended) if appended else "(none)")
    lines += ["## Full page files BEFORE", ""]
    for pid in (old_id, new_id):
        lines += [f"### {pid}", ""]
        lines += _fenced("", before["pages"][pid] or "(absent)")
    lines += ["## Full page files AFTER", ""]
    for pid in (old_id, new_id):
        lines += [f"### {pid}", ""]
        lines += _fenced("", after["pages"][pid] or "(absent)")
    with out_path.open("w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(lines) + "\n")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        prog="consolidate_entity",
        description="Merge a split entity wiki page into its canonical page "
                    "(append-only; retires the old page). Run against a SCRATCH copy "
                    "first; the live-store run is user-signed.")
    ap.add_argument("--store", required=True, help="store root (contains wiki/ and findings/)")
    ap.add_argument("--old", required=True, help="the split page id, e.g. entity:nvda")
    ap.add_argument("--into", required=True, help="the canonical page id, e.g. entity:nvidia")
    ap.add_argument("--as-of", required=True, dest="as_of",
                    help="consolidation vintage label (no wall-clock is ever read)")
    ap.add_argument("--diff-out", required=True, dest="diff_out",
                    help="path for the full before/after diff artifact (markdown)")
    args = ap.parse_args(argv)
    root = pathlib.Path(args.store)
    store = WikiStore(root / "wiki", FindingStore(root / "findings"))
    before = _snapshot(root, [args.old, args.into])
    shapes_before = {pid: _shape(store, pid) for pid in (args.old, args.into)}
    try:
        report = consolidate(store, args.old, args.into, as_of=args.as_of)
    except ConsolidationConflict as exc:
        print(f"CONSOLIDATION-CONFLICT (QUESTION-STOP): {exc}", file=sys.stderr)
        return 2
    after = _snapshot(root, [args.old, args.into])
    shapes_after = {pid: _shape(store, pid) for pid in (args.old, args.into)}
    write_diff_artifact(pathlib.Path(args.diff_out), old_id=args.old, new_id=args.into,
                        as_of=args.as_of, store_root=root, before=before, after=after,
                        shapes_before=shapes_before, shapes_after=shapes_after,
                        report=report)
    print(report.model_dump_json(indent=2))
    print(f"diff artifact: {args.diff_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
