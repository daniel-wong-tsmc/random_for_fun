"""gpu_agent/corpus.py — the flagship input corpus (F62; F78 Stage 3: ages via the wiki).

Read-only consumer of existing stores: the wiki (page index + observations) as the
category-scoped index over the canonical FindingStore, and the L2 dedup classifier for
fresh-vs-store classification. Assembles the AGED accumulated store findings plus this
cycle's fresh gated findings into ONE merged corpus for the judge/thesis brains and the
scorecard, and reports coverage so the gather can run as a top-up.

F78 Stage 3 (D4): the flat 45-day `asOf` window is gone. A store fact now survives on its
decayed effective salience — the page's intrinsic salience (floored at the wiki's
salience_floor, as _score_move already treats it) decayed over the fact's REAL age in
calendar days (`as_of` period-end minus the fact's `observedAt`) via the fact's cadence
half-life — against a salience floor, PLUS its page's lifecycle state (pruned pages
excluded). Genuinely superseded old facts fade toward zero and drop out; a fresh
observation dominates. It reuses the wiki's decay curve unchanged (half_life/decay/
effective_salience, now in calendar days — F78 Stage 1); only the corpus's SELECTION rule
changes.

This module never writes anything: no store mutation, no file writes, no clock reads. All
day-math derives from `asOf`/`observedAt` labels via gpu_agent.asof — never wall-clock — so
replays/backtests are deterministic and a past cycle never sees a future label.
"""
from __future__ import annotations
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field

from gpu_agent.asof import AsOfError, days_between  # F78-3: shared date logic (was corpus-local)
from gpu_agent.gathering.dedup import DEFAULT_DEDUP_CONFIG, FindingClass, classify_findings
from gpu_agent.schema.finding import Finding
from gpu_agent.store import FindingNotFound, FindingStore
from gpu_agent.wiki.lifecycle import DEFAULT_LIFECYCLE_CONFIG
from gpu_agent.wiki.lint import DEFAULT_LINT_CONFIG, effective_salience, half_life
from gpu_agent.wiki.store import WikiStore

# F78 Stage 3: the decayed-effective-salience cutoff below which an aged store fact drops
# from the baseline corpus. This is the wiki's OWN "this fact has faded" line
# (LintConfig.stale_threshold, 0.1) — a decay-based cutoff, never a cycle-count window (D4).
# NOTE: distinct from LintConfig.salience_floor (0.5), which is the intrinsic-salience WEIGHT
# floor reused inside aged_salience below.
SALIENCE_FLOOR_DEFAULT = DEFAULT_LINT_CONFIG.stale_threshold  # 0.1

# TODO (Task 2): WINDOW_DAYS_DEFAULT is deprecated by the aging rule. Kept temporarily
# for assemble/enumerate_store signature compatibility; will be removed in Task 2 refactor.
WINDOW_DAYS_DEFAULT = 45


class CorpusError(ValueError):
    """Raised on canonical-store integrity violations (fail loud). Invalid asOf/observedAt
    labels raise gpu_agent.asof.AsOfError (a sibling ValueError) from the shared date logic."""


def aged_salience(finding: Finding, page_salience: float, as_of: str, horizons,
                  config=DEFAULT_LINT_CONFIG) -> float:
    """A store fact's decayed effective salience at `as_of`: the page's intrinsic salience —
    floored at the wiki's salience_floor so an unscored page still starts from a baseline
    (matching _score_move's `max(salience_floor, page.salience)` treatment) — decayed over the
    fact's REAL age in calendar days (`as_of` period-end minus the fact's `observedAt`, clamped
    at 0) via the fact's cadence half-life. Uses the wiki's own decay/effective_salience curve
    (now in calendar days — F78 Stage 1)."""
    intrinsic = max(config.salience_floor, page_salience)
    age_days = max(0, days_between(as_of, finding.observedAt))
    hl, _ = half_life([finding], horizons, config)
    return effective_salience(intrinsic, age_days, hl)


def _is_pruned(store, page_id, page, lifecycle_config=DEFAULT_LIFECYCLE_CONFIG) -> bool:
    """True iff the page has been lifecycle-pruned. The wiki represents a prune by flooring a
    (previously scored) page's salience to prune_salience_floor via a state-change
    (lifecycle.apply_lifecycle). A page whose salience is at/below that floor AND that carries a
    state-change history was scored then pruned; a never-scored page (salience default 0.0, no
    state-change) is NOT pruned. archived/retired are not wiki-page states in the current model,
    so 'pruned' is the operative lifecycle exclusion."""
    return (page.salience <= lifecycle_config.prune_salience_floor
            and bool(store.state_history(page_id)))


class CoverageEntry(BaseModel):
    entity: str
    indicatorId: str
    count: int
    latestAsOf: str
    latestObservedAt: str


class SkippedPage(BaseModel):
    id: str
    category: Optional[str] = None


class CorpusReport(BaseModel):
    asOf: str
    category: str
    windowDays: int
    windowStart: str   # ISO day, exclusive lower bound
    windowEnd: str     # ISO day, inclusive upper bound
    storeIncluded: list[str] = Field(default_factory=list)      # finding ids, sorted with merged order
    outOfWindow: int = 0
    skippedPages: list[SkippedPage] = Field(default_factory=list)
    freshNew: list[FindingClass] = Field(default_factory=list)
    freshUpdate: list[FindingClass] = Field(default_factory=list)
    freshDuplicate: list[FindingClass] = Field(default_factory=list)
    idOverlaps: list[str] = Field(default_factory=list)
    coverage: list[CoverageEntry] = Field(default_factory=list)
    notCovered: list[str] = Field(default_factory=list)


class CorpusResult(BaseModel):
    merged: list[Finding] = Field(default_factory=list)
    dedupedFresh: list[Finding] = Field(default_factory=list)   # the write-back stream
    report: CorpusReport


def enumerate_store(store_root, category: str, as_of: str,
                    window_days: int) -> tuple[list[Finding], int, list[SkippedPage]]:
    """The windowed store corpus for `category`: every finding observed by a wiki page
    whose header category matches, deduplicated across pages, window-filtered, sorted by
    (asOf, id). Pages with a different or absent category are skipped AND reported (the
    caller logs them — nothing silent). A dangling/unreadable observation finding fails
    loud: the canonical store is trusted input, corruption is a stop-the-line event."""
    store_root = Path(store_root)
    wiki_dir = store_root / "wiki"
    if not wiki_dir.is_dir():
        return [], 0, []   # honest empty: no wiki yet (first-ever cycle)
    store = WikiStore(wiki_dir, FindingStore(store_root / "findings"))
    included: list[Finding] = []
    seen_ids: set[str] = set()
    out_of_window = 0
    skipped: list[SkippedPage] = []
    for entry in store.index():
        if entry.category != category:
            skipped.append(SkippedPage(id=entry.id, category=entry.category))
            continue
        for obs in store.observations(entry.id):
            if obs.findingId in seen_ids:
                continue
            seen_ids.add(obs.findingId)
            try:
                f = store.findings.get(obs.findingId)
            except (FindingNotFound, ValueError) as e:
                raise CorpusError(
                    f"store integrity: page {entry.id} observation references "
                    f"unreadable finding {obs.findingId}: {e}") from e
            if in_window(f.asOf, as_of, window_days):
                included.append(f)
            else:
                out_of_window += 1
    included.sort(key=lambda f: (f.asOf, f.id))
    return included, out_of_window, skipped


def assemble(store_root, category: str, as_of: str, fresh: list[Finding], registry, *,
             window_days: int = WINDOW_DAYS_DEFAULT) -> CorpusResult:
    """The F62 merged corpus: windowed store findings + this cycle's fresh gated
    findings, classified against the store by the existing L2 machinery (intra-batch
    collapse + evidence-merge, then cross-store NEW/UPDATE keep vs DUPLICATE drop).
    The store part is never collapsed: it holds only NEW/UPDATE vintages by
    construction and multiple vintages of one series are deliberate history — scoring
    takes latest-per-series, the judge sees the (dated) evolution. An id overlap means
    the identical finding is already stored: the store copy is kept and the event
    reported. `registry` feeds the coverage table (store part only).
    """
    store_root = Path(store_root)
    store_findings, out_of_window, skipped = enumerate_store(
        store_root, category, as_of, window_days)
    wiki = WikiStore(store_root / "wiki", FindingStore(store_root / "findings"))
    res = classify_findings(fresh, wiki, config=DEFAULT_DEDUP_CONFIG)
    store_ids = {f.id for f in store_findings}
    id_overlaps = sorted(f.id for f in res.outFindings if f.id in store_ids)
    fresh_keeps = [f for f in res.outFindings if f.id not in store_ids]
    merged = store_findings + fresh_keeps
    end = period_end(as_of)
    cov_entries, not_covered = coverage(store_findings, registry)
    report = CorpusReport(
        asOf=as_of, category=category, windowDays=window_days,
        windowStart=(end - datetime.timedelta(days=window_days)).isoformat(),
        windowEnd=end.isoformat(),
        storeIncluded=[f.id for f in store_findings],
        outOfWindow=out_of_window, skippedPages=skipped,
        freshNew=res.new, freshUpdate=res.update, freshDuplicate=res.duplicate,
        idOverlaps=id_overlaps,
        coverage=cov_entries, notCovered=not_covered,
    )
    return CorpusResult(merged=merged, dedupedFresh=fresh_keeps, report=report)


def coverage(store_findings: list[Finding], registry) -> tuple[list[CoverageEntry], list[str]]:
    """Per (entity, indicatorId) over the windowed STORE part: count + latest vintage.
    not_covered = every registered indicator id with zero windowed store findings
    (price included — the gather top-up aims at these). Sorted, deterministic."""
    by_key: dict[tuple[str, str], list[Finding]] = {}
    for f in store_findings:
        by_key.setdefault((f.entity, f.indicatorId), []).append(f)
    entries: list[CoverageEntry] = []
    for (entity, ind), fs in sorted(by_key.items()):
        latest = max(fs, key=lambda f: (f.asOf, f.observedAt, f.id))
        entries.append(CoverageEntry(entity=entity, indicatorId=ind, count=len(fs),
                                     latestAsOf=latest.asOf,
                                     latestObservedAt=latest.observedAt))
    covered = {ind for (_entity, ind) in by_key}
    not_covered = [i for i in sorted(registry.indicators) if i not in covered]
    return entries, not_covered


def render_coverage_text(report: CorpusReport) -> str:
    """Deterministic coverage block for the gather-category dispatch (run-cycle step a0):
    one header line naming the window, one line per covered series, one not-covered line."""
    lines = [f"STORE COVERAGE (window {report.windowStart} < asOf <= "
             f"{report.windowEnd}, {len(report.storeIncluded)} finding(s)):"]
    if not report.coverage:
        lines.append("  (no store coverage — full gather)")
    for c in report.coverage:
        lines.append(f"  {c.entity} {c.indicatorId}: {c.count} finding(s), "
                     f"latest asOf {c.latestAsOf} (observed {c.latestObservedAt})")
    if report.notCovered:
        lines.append("  not covered: " + ", ".join(report.notCovered))
    return "\n".join(lines)
