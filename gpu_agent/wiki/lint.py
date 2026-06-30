from __future__ import annotations
from typing import Optional
from pydantic import BaseModel, Field
from gpu_agent.wiki.store import WikiStore
from gpu_agent.registry.horizon import IndicatorHorizons
from gpu_agent.registry.indicators import IndicatorRegistry, RegistryError
from gpu_agent.wiki.ingest import parse_contradiction_detail


class IndicatorMove(BaseModel):
    indicatorId: str
    magnitude: int
    scoring: bool


class MoveFactors(BaseModel):
    newThread: bool = False
    stateTransition: Optional[dict] = None
    contradiction: bool = False
    contradictionNote: str = ""
    indicatorMoves: list[IndicatorMove] = Field(default_factory=list)


class MaterialMove(BaseModel):
    pageId: str
    title: str
    type: str
    status: str
    score: float
    factors: MoveFactors
    contributingFindingIds: list[str] = Field(default_factory=list)
    tierMult: float
    recencyMult: float
    effectiveSalience: float


class CrossRefGap(BaseModel):
    source: str
    target: str
    reason: str


class ContradictionEntry(BaseModel):
    pageId: str
    note: str
    asOf: str


class StaleEntry(BaseModel):
    pageId: str
    effectiveSalience: float


class HealthReport(BaseModel):
    orphans: list[str] = Field(default_factory=list)
    stale: list[StaleEntry] = Field(default_factory=list)
    crossRefGaps: list[CrossRefGap] = Field(default_factory=list)
    contradictions: list[ContradictionEntry] = Field(default_factory=list)


class LintReport(BaseModel):
    asOf: str
    prevAsOf: Optional[str] = None
    material: list[MaterialMove] = Field(default_factory=list)
    dropped: list[MaterialMove] = Field(default_factory=list)
    health: HealthReport


class LintConfig(BaseModel):
    w_contra: float = 1.0
    w_state: float = 0.6
    w_new: float = 0.5
    w_ind: float = 0.3
    tier_primary: float = 1.0
    tier_secondary: float = 0.6
    recency_full: float = 1.0
    recency_decayed: float = 0.7
    horizon_boost_leading: float = 0.5
    salience_floor: float = 0.5
    material_threshold: float = 0.3
    h_short: int = 1
    h_med: int = 3
    h_long: int = 6
    stale_threshold: float = 0.1


DEFAULT_LINT_CONFIG = LintConfig()

_CADENCE_HL = {"daily": "h_short", "weekly": "h_med", "quarterly": "h_long"}


def _findings_for(store, page_id, observations):
    """Resolve observation finding ids to Findings, skipping any not in the FindingStore."""
    out = []
    for o in observations:
        try:
            out.append(store.findings.get(o.findingId))
        except Exception:
            continue
    return out


def half_life(findings, horizons, config=DEFAULT_LINT_CONFIG):
    """Longest-persistence half-life (in cycles) among the findings' cadence-horizon tags.
    cadence drives persistence (daily->short, weekly->med, quarterly->long); a leading-horizon
    finding is floored at H_med. Untagged indicator ids fall back to H_med and are RETURNED
    (the caller logs them — nothing silent). No findings -> H_med (neutral)."""
    untagged: list[str] = []
    classes: list[int] = []
    for f in findings:
        tag = horizons.get(f.indicatorId)
        if tag is None or tag.get("cadence") not in _CADENCE_HL:
            untagged.append(f.indicatorId)
            classes.append(config.h_med)
            continue
        hl = getattr(config, _CADENCE_HL[tag["cadence"]])
        if tag.get("horizon") == "leading":
            hl = max(hl, config.h_med)
        classes.append(hl)
    return (max(classes) if classes else config.h_med), untagged


def quiet_age(store, page_id, as_of) -> int:
    """Number of distinct asOf cycles in the log strictly after the page's last MATERIAL event
    (append-observation or state-change), up to as_of. A body-only edit is not material. A page
    with no material events decays from its createdAsOf."""
    events = [e for e in store.log.read() if e.asOf <= as_of]
    cycles = sorted({e.asOf for e in events})
    materials = [e.asOf for e in events
                 if e.pageId == page_id and e.kind in ("append-observation", "state-change")]
    baseline = max(materials) if materials else store.get_page(page_id).createdAsOf
    return sum(1 for c in cycles if c > baseline)


def decay(quiet_age: int, half_life: int) -> float:
    return 0.5 ** (quiet_age / half_life)


def effective_salience(intrinsic: float, quiet_age: int, half_life: int) -> float:
    return intrinsic * decay(quiet_age, half_life)


def _is_scoring(registry, indicator_id):
    """True iff the indicator contributes to the index (the frozen dmi_smi split:
    scoring AND side not in {price, structural}). None if the id is unregistered."""
    try:
        spec = registry.resolve(indicator_id)
    except RegistryError:
        return None
    return bool(spec.scoring and spec.side not in ("price", "structural"))


def _score_move(store, page_id, *, as_of, prev_as_of, is_new, state_transition,
                contradiction_note, registry, horizons, config=DEFAULT_LINT_CONFIG):
    page = store.get_page(page_id)
    lo = prev_as_of or ""
    window = [o for o in store.observations(page_id) if lo < o.asOf <= as_of]
    contributing = []
    pairs = []  # (observation, finding)
    for o in window:
        try:
            pairs.append((o, store.findings.get(o.findingId)))
            contributing.append(o.findingId)
        except Exception:
            continue

    factors = MoveFactors()
    base = 0.0
    if is_new:
        base += config.w_new
        factors.newThread = True
    if (not is_new) and state_transition is not None:
        base += config.w_state
        factors.stateTransition = state_transition
    if contradiction_note is not None:
        base += config.w_contra
        factors.contradiction = True
        factors.contradictionNote = contradiction_note

    ind_sum = 0
    for _, f in pairs:
        sc = _is_scoring(registry, f.indicatorId)
        scoring = bool(sc)
        factors.indicatorMoves.append(
            IndicatorMove(indicatorId=f.indicatorId, magnitude=f.magnitude, scoring=scoring))
        if scoring:
            ind_sum += f.magnitude
    base += config.w_ind * ind_sum

    has_primary = any(any(e.tier == "primary" for e in f.evidence) for _, f in pairs)
    tier_mult = config.tier_primary if has_primary else config.tier_secondary
    this_cycle = any(o.asOf == as_of for o, _ in pairs)
    recency_mult = config.recency_full if this_cycle else config.recency_decayed
    leading = any((horizons.get(f.indicatorId) or {}).get("horizon") == "leading" for _, f in pairs)
    horizon_boost = config.horizon_boost_leading if leading else 0.0
    salience_weight = max(config.salience_floor, page.salience)
    score = base * tier_mult * recency_mult * (1 + horizon_boost) * salience_weight

    all_findings = _findings_for(store, page_id, store.observations(page_id))
    hl, _untagged = half_life(all_findings, horizons, config)
    eff = effective_salience(page.salience, quiet_age(store, page_id, as_of), hl)

    return MaterialMove(pageId=page_id, title=page.title, type=page.type, status=page.status,
                        score=score, factors=factors, contributingFindingIds=contributing,
                        tierMult=tier_mult, recencyMult=recency_mult, effectiveSalience=eff)


def health_report(store, *, as_of, contradictions, horizons, config=DEFAULT_LINT_CONFIG):
    """Structural health over ALL pages (entity AND theme): orphans, stale (decayed), cross-ref
    gaps (asymmetric + mention-without-link), and the contradiction roll-up. Read-only; mutates
    nothing."""
    idx = store.index()
    pages = {e.id: store.get_page(e.id) for e in idx}

    referenced = set()
    for p in pages.values():
        referenced.update(p.crossRefs)
    orphans = sorted(pid for pid in pages if pid not in referenced)

    stale = []
    for pid, p in pages.items():
        qa = quiet_age(store, pid, as_of)
        if qa <= 0:
            continue  # a fresh page is never "stale"
        hl, _ = half_life(_findings_for(store, pid, store.observations(pid)), horizons, config)
        eff = effective_salience(p.salience, qa, hl)
        if eff < config.stale_threshold:
            stale.append(StaleEntry(pageId=pid, effectiveSalience=eff))
    stale.sort(key=lambda s: s.pageId)

    gaps = []
    for pid, p in sorted(pages.items()):
        for ref in p.crossRefs:
            if ref in pages and pid not in pages[ref].crossRefs:
                gaps.append(CrossRefGap(source=pid, target=ref, reason="asymmetric"))
    for pid, p in sorted(pages.items()):
        body = store.window(pid, 0).body
        for other_id, other in sorted(pages.items()):
            if other_id == pid or not other.title:
                continue
            if other.title in body and other_id not in p.crossRefs:
                gaps.append(CrossRefGap(source=pid, target=other_id, reason="mention-without-link"))

    contras = [ContradictionEntry(pageId=pid, note=note, asOf=as_of)
               for pid, note in sorted(contradictions.items())]

    return HealthReport(orphans=orphans, stale=stale, crossRefGaps=gaps, contradictions=contras)


def score_moves(store, diff, contradictions, *, as_of, prev_as_of, registry, horizons,
                config=DEFAULT_LINT_CONFIG):
    """Assemble the move-set (diff pages + any contradicted page), score each, split on the
    material threshold. Both lists are ranked by score descending."""
    new_ids = {pd.id for pd in diff.new_pages}
    delta_by_id = {pd.id: pd for pd in (list(diff.new_pages) + list(diff.changed_pages))}
    im_by_id = {im.id: im for im in diff.index_moves}
    move_ids = (new_ids | {pd.id for pd in diff.changed_pages}
                | set(im_by_id) | set(contradictions))
    material, dropped = [], []
    for pid in sorted(move_ids):
        is_new = pid in new_ids
        st = None
        if not is_new:
            delta = delta_by_id.get(pid)
            if delta is not None and delta.stateTransition is not None:
                st = delta.stateTransition
            elif pid in im_by_id:
                im = im_by_id[pid]
                st = {"from": im.oldState, "to": im.newState}
        note = contradictions.get(pid)  # None when the page has no contradiction this cycle
        mv = _score_move(store, pid, as_of=as_of, prev_as_of=prev_as_of, is_new=is_new,
                         state_transition=st, contradiction_note=note,
                         registry=registry, horizons=horizons, config=config)
        (material if mv.score >= config.material_threshold else dropped).append(mv)
    material.sort(key=lambda m: m.score, reverse=True)
    dropped.sort(key=lambda m: m.score, reverse=True)
    return material, dropped


def _auto_prev(store, as_of):
    cycles = sorted({e.asOf for e in store.log.read() if e.asOf < as_of})
    return cycles[-1] if cycles else None


def _contradictions_for(store, as_of):
    out = {}
    for e in store.log.read():
        if e.kind == "ingest" and e.asOf == as_of:
            for c in parse_contradiction_detail(e.detail)["contradictions"]:
                out[c["pageId"]] = c["note"]
    return out


def lint(store, *, as_of, prev_as_of=None, registry, horizons, config=DEFAULT_LINT_CONFIG) -> LintReport:
    """The wiki lint / early-warning pass: rank the cycle's material moves, decay quiet threads,
    surface structural health. Pure, read-only except for one idempotent `lint` provenance event."""
    if prev_as_of is None:
        prev_as_of = _auto_prev(store, as_of)
    diff = store.diff(as_of, prev_as_of or "")
    contradictions = _contradictions_for(store, as_of)
    material, dropped = score_moves(store, diff, contradictions, as_of=as_of, prev_as_of=prev_as_of,
                                    registry=registry, horizons=horizons, config=config)
    health = health_report(store, as_of=as_of, contradictions=contradictions,
                            horizons=horizons, config=config)
    report = LintReport(asOf=as_of, prevAsOf=prev_as_of, material=material,
                        dropped=dropped, health=health)
    if not any(e.kind == "lint" and e.asOf == as_of for e in store.log.read()):
        detail = (f"material {len(material)}; dropped {len(dropped)}; stale {len(health.stale)}; "
                  f"orphans {len(health.orphans)}; contradictions {len(health.contradictions)}")
        store.log.append(asOf=as_of, kind="lint", detail=detail)
    return report
