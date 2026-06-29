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


class PageEnrichment(BaseModel):
    pageId: str
    bodyMarkdown: str
    state: str
    trajectory: str
    salience: float
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
