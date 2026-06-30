from __future__ import annotations
import re
from pydantic import BaseModel, Field
from gpu_agent.schema.finding import Finding
from gpu_agent.wiki.store import WikiStore, PageNotFound

INGEST_SYSTEM = (
    "You curate a per-entity wiki of the GPU market. For each entity page you are given its "
    "standing thesis (current state/trajectory/body) and the day's new GATED findings. Return an "
    "IngestResult: for each page, write a concise markdown body that synthesizes the thesis with "
    "the new findings (every claim must cite a finding id like [f-123]); set a short state and a "
    "trajectory ('from -> to'); set a salience in [0,1] for how much this page matters now; list "
    "crossRefs to other entity page ids you mention; and set contradictsThesis=true with a short "
    "contradictionNote when a new finding opposes the page's current state. Never invent numbers — "
    "only cite what the findings state. Only enrich pages you were given; do not invent page ids."
)

_SLUG_RE = re.compile(r"[^a-z0-9]+")


def slug(entity: str) -> str:
    s = _SLUG_RE.sub("-", entity.strip().lower()).strip("-")
    if not s:
        raise ValueError(f"unroutable entity (empty slug): {entity!r}")
    return s


def format_contradiction_detail(enriched_count: int, contradictions: list[tuple[str, str]]) -> str:
    """Canonical ingest-event detail. `contradictions` is a list of (pageId, note). One source of
    format truth, shared by apply_enrichment (writer) and the lint pass (reader)."""
    detail = f"enriched {enriched_count} page(s)"
    if contradictions:
        detail += "; contradictions: " + " | ".join(f"{pid}: {note}" for pid, note in contradictions)
    return detail


def parse_contradiction_detail(detail: str) -> dict:
    """Inverse of format_contradiction_detail. Note: a note containing ' | ' would over-split; notes
    are short phrases and this is our own controlled format (round-trip tested)."""
    count = 0
    m = re.match(r"enriched (\d+) page\(s\)", detail)
    if m:
        count = int(m.group(1))
    contradictions: list[dict] = []
    marker = "; contradictions: "
    idx = detail.find(marker)
    if idx != -1:
        rest = detail[idx + len(marker):]
        for part in rest.split(" | "):
            pid, sep, note = part.partition(": ")  # pageId has no ': ' (colon-space); first split is the boundary
            if sep:
                contradictions.append({"pageId": pid, "note": note})
    return {"count": count, "contradictions": contradictions}


class PageEnrichment(BaseModel):
    pageId: str
    bodyMarkdown: str
    state: str
    trajectory: str
    salience: float = Field(ge=0.0, le=1.0)
    crossRefs: list[str] = Field(default_factory=list)
    contradictsThesis: bool = False
    contradictionNote: str = ""


class IngestResult(BaseModel):
    pages: list[PageEnrichment]


def _entity_page_id(finding: Finding) -> str:
    if not finding.entity or not finding.entity.strip():
        raise ValueError(f"finding {finding.id} has empty entity; cannot route")
    return f"entity:{slug(finding.entity)}"


def route_findings(store: WikiStore, findings: list[Finding], *, as_of: str,
                   category: str | None = None) -> list[str]:
    """Phase 1 (deterministic): append each gated finding to its entity page, idempotently.
    Returns the sorted list of touched page ids."""
    touched: set[str] = set()
    for f in findings:
        pid = _entity_page_id(f)
        store.findings.append(f)  # gate-store (idempotent; differing content on a reused id fails loud)
        try:
            store.get_page(pid)
        except PageNotFound:
            store.create_page(pid, "entity", f.entity, category=category, as_of=as_of)
        already = {o.findingId for o in store.observations(pid)}
        if f.id not in already:
            store.append_observation(pid, f.id, as_of=as_of)
        touched.add(pid)
    return sorted(touched)


def build_bundle(store: WikiStore, findings: list[Finding], touched: list[str], *, as_of: str) -> dict:
    """Phase 2 emit: the bundle the brain answers. One entry per touched entity page, with its
    current header + body and the day's findings on it."""
    by_page: dict[str, list[Finding]] = {}
    for f in findings:
        by_page.setdefault(_entity_page_id(f), []).append(f)
    pages = []
    for pid in touched:
        view = store.window(pid, 0)  # page + body (no observations needed)
        page = view.page
        pages.append({
            "pageId": pid,
            "title": page.title,
            "currentState": page.state,
            "currentTrajectory": page.trajectory,
            "currentSalience": page.salience,
            "currentCrossRefs": page.crossRefs,
            "currentBody": view.body,
            "newFindings": [
                {"id": f.id, "statement": f.statement, "why": f.why,
                 "impact": f.impact.model_dump(),
                 "evidence": [e.model_dump() for e in f.evidence]}
                for f in by_page.get(pid, [])
            ],
        })
    return {"system": INGEST_SYSTEM, "schema": IngestResult.model_json_schema(),
            "asOf": as_of, "pages": pages}


def apply_enrichment(store: WikiStore, result: IngestResult, *, as_of: str) -> None:
    """Phase 2 (deterministic apply): enrich existing entity pages from the brain's IngestResult.
    Rejects non-entity / missing pages loud. Idempotent set_body/record_state/crossRefs. Appends
    exactly one 'ingest' log event per as_of (contradictions recorded in its detail, not yet weighted)."""
    contradictions: list[tuple[str, str]] = []
    for pe in result.pages:
        if not pe.pageId.startswith("entity:"):
            raise ValueError(f"enrichment targets non-entity page: {pe.pageId}")
        page = store.get_page(pe.pageId)  # raises PageNotFound (loud) if missing
        store.set_body(pe.pageId, pe.bodyMarkdown, as_of=as_of)  # idempotent
        if (page.state, page.trajectory, page.salience) != (pe.state, pe.trajectory, pe.salience):
            store.record_state(pe.pageId, as_of=as_of, state=pe.state,
                               trajectory=pe.trajectory, salience=pe.salience)
        if page.crossRefs != pe.crossRefs:
            store.update_header(pe.pageId, as_of=as_of, crossRefs=pe.crossRefs)
        if pe.contradictsThesis:
            contradictions.append((pe.pageId, pe.contradictionNote))
    already_logged = any(e.kind == "ingest" and e.asOf == as_of for e in store.log.read())
    if not already_logged:
        detail = format_contradiction_detail(len(result.pages), contradictions)
        store.log.append(asOf=as_of, kind="ingest", detail=detail)
