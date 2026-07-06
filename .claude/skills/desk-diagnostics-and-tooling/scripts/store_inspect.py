#!/usr/bin/env python3
"""store_inspect.py -- read-only recipes for the store/ tree (scorecards, findings,
dedup reports, wiki lint history, thesis book/history integrity).

STDLIB ONLY. Read-only: never writes store/, never calls the gpu_agent CLI in a way that
could append a log event (wiki-lint's CLI form is NOT purely read-only -- see the
`wiki-lint` subcommand's docstring below for why this script reads log.jsonl directly
instead of invoking it).

Usage (from repo root, or pass --repo):
    .venv/Scripts/python ...\\store_inspect.py latest --category chips.merchant-gpu
    .venv/Scripts/python ...\\store_inspect.py findings --category chips.merchant-gpu
    .venv/Scripts/python ...\\store_inspect.py dedup --category chips.merchant-gpu --as-of 2026-07-05
    .venv/Scripts/python ...\\store_inspect.py wiki-lint
    .venv/Scripts/python ...\\store_inspect.py thesis --category chips.merchant-gpu

Exit codes: 0 = read succeeded / no anomaly; 1 = anomaly found (e.g. thesis book/history
divergence, or an explicit --check flag failed); 2 = operator error (bad path, bad args).
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

# Mirrors gpu_agent/report.py::_VERSION_RE. asOf is month grain (YYYY-MM) or day grain
# (YYYY-MM-DD); this is the ONLY pattern the frozen store/scoring code recognizes as a
# scorecard filename -- anything else under store/<category>/ is not a scorecard (dedup
# reports live in the same directory and do NOT match this).
_VERSION_RE = re.compile(r"^(\d{4}-\d{2}(?:-\d{2})?)-v(\d+)\.json$")


def find_repo_root(start: Path) -> Path | None:
    proc = subprocess.run(["git", "-C", str(start), "rev-parse", "--show-toplevel"],
                           capture_output=True, encoding="utf-8", errors="replace")
    if proc.returncode != 0:
        return None
    return Path(proc.stdout.strip())


# ── latest ────────────────────────────────────────────────────────────────────

def cmd_latest(repo: Path, category: str) -> int:
    """Two orderings, printed side by side, because they can disagree (the mixed-grain
    trap): CODE ORDER is exactly what gpu_agent.report.find_prior / memory.py's
    latest_scorecard_before use -- lexical sort of the raw asOf STRING, descending. Because
    "2026-07" is a PREFIX of "2026-07-05", Python string comparison ranks "2026-07-05" as
    lexically GREATER than "2026-07" (a shorter string that is a prefix of a longer one
    sorts first ascending / last descending) -- so a daily run's day-grain asOf sorts as
    "more recent" than a monthly flagship's month-grain asOf in the SAME directory, even
    when the flagship was produced later in wall-clock time. CALENDAR ORDER treats month
    grain as spanning through the end of that month, which is the reading a human expects.
    When they disagree, CODE ORDER is what any tool that calls find_prior()/
    latest_scorecard_before() with no explicit path will actually pick -- verify which one
    matters for your task before trusting either "latest" label."""
    cat_dir = repo / "store" / category
    if not cat_dir.is_dir():
        print(f"error: no store/{category}/ directory", file=sys.stderr)
        return 2
    candidates = []
    unmatched = []
    for p in sorted(cat_dir.glob("*.json")):
        m = _VERSION_RE.match(p.name)
        if m:
            candidates.append((m.group(1), int(m.group(2)), p.name))
        else:
            unmatched.append(p.name)
    if not candidates:
        print(f"no scorecards found under store/{category}/ (found {len(unmatched)} "
              f"non-scorecard file(s): {', '.join(unmatched) or 'none'})")
        return 0

    code_order = sorted(candidates, key=lambda t: (t[0], t[1]), reverse=True)

    def cal_key(asof: str):
        # Normalize for a true calendar comparison: month grain sorts as the LAST instant
        # of that month (so "2026-07" reads as after every day within 2026-07, matching
        # the "the monthly flagship rolls up the whole month" mental model).
        parts = asof.split("-")
        if len(parts) == 2:
            return (int(parts[0]), int(parts[1]), 32)  # 32 > any real day-of-month
        return (int(parts[0]), int(parts[1]), int(parts[2]))

    cal_order = sorted(candidates, key=lambda t: (cal_key(t[0]), t[1]), reverse=True)

    print(f"store/{category}/  ({len(candidates)} scorecard(s), {len(unmatched)} "
          f"non-scorecard file(s) present: {', '.join(unmatched) or 'none'})")
    print(f"  CODE ORDER   'latest' (find_prior/latest_scorecard_before lexical sort): "
          f"{code_order[0][2]}")
    print(f"  CALENDAR ORDER 'latest' (true chronological, month-grain = end of month): "
          f"{cal_order[0][2]}")
    if code_order[0][2] != cal_order[0][2]:
        print("  MIXED GRAIN: the two orderings DISAGREE. Any caller that auto-detects "
              "'latest' with no explicit filename (find_prior with current_path=None, "
              "memory.latest_scorecard_before) will silently pick the CODE ORDER file, "
              "not the calendar-latest one. Pass an explicit --scorecard path if you mean "
              "the calendar-latest one instead.")
        return 0
    print("  Orderings agree (no grain-mixing hazard for this directory right now).")
    return 0


# ── findings ──────────────────────────────────────────────────────────────────

def cmd_findings(repo: Path) -> int:
    """Census of store/findings/ (Part 9 append-only FindingStore -- one JSON file per
    finding id; by construction it holds only findings that already PASSED gate.check_finding,
    so there is no "gate outcome" field to break down here -- rejected drafts never reach
    this directory at all. For pass/reject counts, see eval_diagnostics.py's case-census
    (fixtures/evals/cases/*.json checks.gateOutcome), a genuinely different, eval-only
    concept that happens to share the word "gate". No --category filter: Finding carries no
    top-level category field (only one category is live in this store today; a second
    category would need its own store/<id>/ tree per the .gitignore whitelist anyway)."""
    fdir = repo / "store" / "findings"
    if not fdir.is_dir():
        print("error: no store/findings/ directory", file=sys.stderr)
        return 2
    files = sorted(fdir.glob("*.json"))
    by_kind = Counter()
    by_side = Counter()
    by_indicator = Counter()
    pre_f52 = 0   # id shape <slug>-<hash8>-<n>          (no asOf segment)
    post_f52 = 0  # id shape <slug>-<hash8>-<asOf>-<n>    (vintage-scoped, F52)
    id_re_post = re.compile(r"-\d{4}-\d{2}(?:-\d{2})?-\d+$")
    for p in files:
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        by_kind[d.get("kind", "?")] += 1
        by_side[d.get("side", "?")] += 1
        by_indicator[d.get("indicatorId", "?")] += 1
        if id_re_post.search(d.get("id", p.stem)):
            post_f52 += 1
        else:
            pre_f52 += 1

    print(f"store/findings/: {len(files)} finding(s)")
    print(f"  by kind:      {dict(by_kind)}")
    print(f"  by side:      {dict(by_side)}")
    print(f"  id generation: {post_f52} vintage-scoped (post-F52, id ends -<asOf>-<n>), "
          f"{pre_f52} legacy (pre-F52, id ends -<n> only) -- both are valid, coexisting "
          f"generations; do not treat the legacy shape as corrupt.")
    top = by_indicator.most_common(5)
    print(f"  top indicators by finding count: {top}")
    return 0


# ── dedup ─────────────────────────────────────────────────────────────────────

def cmd_dedup(repo: Path, category: str, as_of: str | None) -> int:
    """Reads store/<category>/dedup-<asOf>.json -- the L2 (finding-level) dedup report.
    Reminder of the two-layer model: L1 is DOCUMENT-level and lives in store/seen_docs.jsonl
    (keyed by content HASH first, normalized URL second -- see that file's own header
    comment); L2 is FINDING-level and lives here, keyed by (entity, indicatorId) normally,
    or the F51 price-series 4-tuple (entity, indicatorId, publisher-netloc, unit) for
    side=='price' findings. A dedup report only tells you about L2; it says nothing about
    how many raw documents L1 filtered out before extraction ever ran (that count is
    docsDroppedKnown here, if the run threaded --dedup-store through ingest at all)."""
    cat_dir = repo / "store" / category
    if as_of:
        candidates = [cat_dir / f"dedup-{as_of}.json"]
    else:
        candidates = sorted(cat_dir.glob("dedup-*.json"))
    candidates = [c for c in candidates if c.exists()]
    if not candidates:
        print(f"no dedup-*.json found under store/{category}/"
              + (f" for asOf={as_of}" if as_of else ""), file=sys.stderr)
        return 2
    for path in candidates:
        d = json.loads(path.read_text(encoding="utf-8"))
        new_, upd, dup = d.get("findingsNew", []), d.get("findingsUpdate", []), d.get("findingsDuplicate", [])
        dropped = d.get("docsDroppedKnown", [])
        print(f"{path.name}  (asOf={d.get('asOf')})")
        print(f"  L1 docs dropped as already-known: {len(dropped)}")
        print(f"  L2 new={len(new_)} update={len(upd)} duplicate={len(dup)}")
        for label, group in (("update", upd), ("duplicate", dup)):
            for entry in group[:5]:
                print(f"    [{label}] {entry.get('findingId')} <- prior "
                      f"{entry.get('priorFindingId')}: {entry.get('detail')}")
            if len(group) > 5:
                print(f"    ... and {len(group) - 5} more {label} entr(y/ies)")
    return 0


# ── wiki-lint ─────────────────────────────────────────────────────────────────

def cmd_wiki_lint(repo: Path) -> int:
    """Reads store/wiki/log.jsonl DIRECTLY and reports the most recent 'lint' event, rather
    than invoking `gpu-agent wiki-lint` (whose CLI form calls the real `lint()` function with
    its default record=True -- it appends a NEW lint event to log.jsonl the first time it is
    called for a given as_of, which is a WRITE to the tracked store; it is only a no-op on a
    SECOND call for an as_of already linted, per lint()'s own idempotency comment in
    gpu_agent/wiki/lint.py. This script must stay read-only regardless of as_of, so it never
    shells out to that CLI form -- it only reads what has already been recorded.)"""
    log_path = repo / "store" / "wiki" / "log.jsonl"
    if not log_path.exists():
        print("no store/wiki/log.jsonl found", file=sys.stderr)
        return 2
    lines = log_path.read_text(encoding="utf-8").splitlines()
    events = [json.loads(ln) for ln in lines if ln.strip()]
    lints = [e for e in events if e.get("kind") == "lint"]
    print(f"store/wiki/log.jsonl: {len(events)} event(s) total, {len(lints)} lint event(s)")
    if not lints:
        print("  no lint has ever been recorded for this store.")
        return 0
    last = lints[-1]
    print(f"  latest lint (seq {last['seq']}, asOf {last['asOf']}): {last['detail']}")
    print("  INTERPRETATION: 'material N' = pages the lint ranked as containing a "
          "cycle-worthy move this asOf; 'dropped N' = candidate moves scored below the "
          "materiality threshold (F34 fold, not an error); 'stale N' = pages whose "
          "half-life decay has run past the staleness config with no fresh observation "
          "(candidates for the lifecycle prune pass, F25/lifecycle-related, not "
          "auto-removed); 'orphans N' = observations or cross-refs pointing at findings/"
          "pages lint could not resolve (data-quality signal, not fatal); 'contradictions "
          "N' = pages where a fresh observation conflicts with the page's own trajectory "
          "(surfaced, never silently resolved). These counts accumulate with NO landed "
          "cleanup mechanism as of this writing (open problem, F25-adjacent) -- a nonzero "
          "'stale'/'orphans' count is expected background noise, not by itself an alarm; "
          "watch the TREND across lint events, not a single snapshot.")
    return 0


# ── thesis ────────────────────────────────────────────────────────────────────

def cmd_thesis(repo: Path, category: str) -> int:
    """Checks store/theses/<category>/book.json against history.jsonl's replay -- the same
    check ThesisStore.load() performs before ANY code trusts book.json (charter Part 9 /
    gpu_agent/thesis.py: history.jsonl is canonical; load() hard-fails loud on divergence
    rather than silently repairing or picking a side).

    Deliberately does NOT reimplement apply_record()'s fold in this script: an early draft
    did (a "read a JSONL, fold dicts by id" reimplementation, stdlib-only) and it produced a
    FALSE divergence alarm on a perfectly healthy book -- ThesisEntry carries derived fields
    (streak, pendingChallenge, lastDirection, provenance...) that a naive last-write-wins
    dict-merge does not reproduce byte-for-byte, so "my replay disagrees with book.json"
    proved the reimplementation was incomplete, not that the store was tampered. Getting
    this wrong in the ALARMING direction is worse than not shipping the check at all, so
    this instead subprocesses the repo's own venv to call the real ThesisStore.load() --
    still read-only (load() only reads book.json + history.jsonl), and it is the actual
    logic that gates every real caller, not a lookalike of it.

    What divergence MEANS if you ever see this exit 1: book.json and history.jsonl
    disagree. It means someone/something wrote book.json directly instead of going through
    ThesisStore.write() (which always appends to history.jsonl FIRST). Never hand-edit
    book.json back into shape; replay history.jsonl (this same command re-run once the
    divergence is fixed) to see what the store's own logic thinks the book should be, and
    find what produced the direct write."""
    root = repo / "store" / "theses" / category
    book_path, hist_path = root / "book.json", root / "history.jsonl"
    if not book_path.exists():
        print(f"no thesis book at {book_path}", file=sys.stderr)
        return 2
    on_disk = json.loads(book_path.read_text(encoding="utf-8"))
    n_hist = sum(1 for ln in hist_path.read_text(encoding="utf-8").splitlines() if ln.strip()) \
        if hist_path.exists() else 0
    print(f"store/theses/{category}/: book.json has {len(on_disk.get('entries', []))} "
          f"entries; history.jsonl has {n_hist} record(s).")

    py_candidates = [repo / ".venv" / "Scripts" / "python.exe", repo / ".venv" / "bin" / "python"]
    py = next((p for p in py_candidates if p.exists()), None)
    if py is None:
        print("  no .venv found -- cannot run the authoritative ThesisStore.load() check "
              "from here. Run from the repo root with its venv, or by hand:\n"
              "  .venv/Scripts/python -c \"from gpu_agent.thesis import ThesisStore; "
              f"ThesisStore('store/theses/{category}').load()\"")
        return 2

    snippet = (
        "from gpu_agent.thesis import ThesisStore, ThesisStoreError\n"
        f"s = ThesisStore(r'store/theses/{category}')\n"
        "try:\n"
        "    b = s.load()\n"
        "    print('OK', len(b.entries))\n"
        "except ThesisStoreError as e:\n"
        "    print('DIVERGE', e)\n"
    )
    proc = subprocess.run([str(py), "-c", snippet], cwd=str(repo), capture_output=True,
                          encoding="utf-8", errors="replace")
    out = (proc.stdout or "").strip()
    if out.startswith("OK"):
        print(f"  OK: ThesisStore.load() succeeded ({out}) -- book.json matches "
              f"history.jsonl's replay, no divergence.")
        return 0
    print(f"  DIVERGENCE (or load error): {out or proc.stderr.strip()}")
    return 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                  formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--repo", default=".", help="repo root (default: cwd, auto-detected via git)")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_latest = sub.add_parser("latest")
    p_latest.add_argument("--category", required=True)

    sub.add_parser("findings")

    p_dedup = sub.add_parser("dedup")
    p_dedup.add_argument("--category", required=True)
    p_dedup.add_argument("--as-of", default=None)

    sub.add_parser("wiki-lint")

    p_thesis = sub.add_parser("thesis")
    p_thesis.add_argument("--category", required=True)

    args = ap.parse_args()
    repo = find_repo_root(Path(args.repo))
    if repo is None:
        print(f"error: {args.repo} is not inside a git repo", file=sys.stderr)
        return 2

    if args.cmd == "latest":
        return cmd_latest(repo, args.category)
    if args.cmd == "findings":
        return cmd_findings(repo)
    if args.cmd == "dedup":
        return cmd_dedup(repo, args.category, args.as_of)
    if args.cmd == "wiki-lint":
        return cmd_wiki_lint(repo)
    if args.cmd == "thesis":
        return cmd_thesis(repo, args.category)
    return 2


if __name__ == "__main__":
    sys.exit(main())
