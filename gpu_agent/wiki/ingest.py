from __future__ import annotations
import re
from pydantic import BaseModel, ConfigDict, Field
from gpu_agent.schema.finding import Finding
from gpu_agent.wiki.store import WikiStore, PageNotFound
from gpu_agent.wiki.salience import computed_salience

INGEST_SYSTEM = (
    "You curate a per-entity wiki of the GPU market. For each entity page you are given its "
    "standing thesis (current state/trajectory/body) and the day's new GATED findings. Return an "
    "IngestResult: for each page, write a concise markdown body that synthesizes the thesis with "
    "the new findings (every claim must cite a finding id like [f-123]); set a short state and a "
    "trajectory ('from -> to'); list crossRefs to other entity page ids you mention; and set "
    "contradictsThesis=true with a short contradictionNote when a new finding opposes the page's "
    "current state. Never invent numbers — only cite what the findings state. Only enrich pages "
    "you were given; do not invent page ids."
)

_SLUG_RE = re.compile(r"[^a-z0-9]+")
_AS_OF_RE = re.compile(r"^\d{4}-\d{2}(-\d{2})?$")


def _check_as_of_grain(as_of: str) -> None:
    if not _AS_OF_RE.match(as_of):
        raise ValueError(f"invalid asOf grain: {as_of!r}")


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
    model_config = ConfigDict(extra="forbid")

    pageId: str
    bodyMarkdown: str
    state: str
    trajectory: str
    crossRefs: list[str] = Field(default_factory=list)
    contradictsThesis: bool = False
    contradictionNote: str = ""


class IngestResult(BaseModel):
    pages: list[PageEnrichment]


class EnrichmentGateError(ValueError):
    """Raised when apply_enrichment's F14 gate rejects one or more pages: an unresolved
    citation or a number with no cited-finding backing. Nothing is written when this fires."""

    def __init__(self, violations: list[str]):
        self.violations = violations
        super().__init__("; ".join(violations))


_CITATION_RE = re.compile(r"\[([A-Za-z0-9][A-Za-z0-9._-]*)\]")
_NUMERIC_RE = re.compile(r"\d[\d,]*(?:\.\d+)?")


def _cited_finding_ids(body: str) -> set[str]:
    return set(_CITATION_RE.findall(body))


def _numeric_tokens(text: str) -> set[str]:
    """Numeric tokens (>= 2 digits after stripping thousands commas) mentioned in `text`.
    Single-digit tokens (list markers like '1.') are not material and are dropped."""
    out: set[str] = set()
    for m in _NUMERIC_RE.findall(text):
        norm = m.replace(",", "")
        if sum(ch.isdigit() for ch in norm) >= 2:
            out.add(norm)
    return out


def _allowed_numeric_tokens(store: WikiStore, cited_ids: set[str], pe: PageEnrichment) -> set[str]:
    """The set of numeric tokens a page body may mention: everything extractable from its cited
    findings (statement, why, value.number renderings, evidence excerpts and dates) plus the
    enrichment's own state/trajectory strings — tokenized with the SAME regex + normalization
    used on the body, so the gate compares token to token, never substring to string (a
    fabricated '20' can no longer ride inside a date like '2026-06-15'). A date tokenizes into
    its honest components ('2026', '06', '15'), each individually citable."""
    parts = [pe.state, pe.trajectory]
    for fid in sorted(cited_ids):
        if not store.findings.exists(fid):
            continue
        f = store.findings.get(fid)
        parts.append(f.statement)
        parts.append(f.why)
        if f.value is not None:
            v = f.value.number
            # Multiple renderings so the body can cite the value however it was written:
            # f"{v:g}" degrades to scientific notation for large floats ("7.52e+10"), so the
            # integral form str(int(v)) is included whenever v is a whole number.
            parts.extend([str(v), repr(v), f"{v:g}"])
            if v.is_integer():
                parts.append(str(int(v)))
        for e in f.evidence:
            parts.append(e.excerpt)
            parts.append(e.date)
    allowed: set[str] = set()
    for p in parts:
        allowed |= _numeric_tokens(p)
    return allowed


def _validate_enrichment_gate(store: WikiStore, pe: PageEnrichment) -> list[str]:
    """F14: every citation must resolve to a gated finding; every number in the body must trace
    to a cited finding (or the enrichment's own state/trajectory) by exact token equality.
    Returns violation strings; empty means the page is clean."""
    violations: list[str] = []
    cited = _cited_finding_ids(pe.bodyMarkdown)
    for token in sorted(cited):
        if not store.findings.exists(token):
            violations.append(f"{pe.pageId}: cites unknown finding {token}")
    allowed = _allowed_numeric_tokens(store, cited, pe)
    for token in sorted(_numeric_tokens(pe.bodyMarkdown)):
        if token not in allowed:
            violations.append(f"{pe.pageId}: uncited number {token}")
    return violations


def _entity_page_id(finding: Finding) -> str:
    if not finding.entity or not finding.entity.strip():
        raise ValueError(f"finding {finding.id} has empty entity; cannot route")
    return f"entity:{slug(finding.entity)}"


def route_findings(store: WikiStore, findings: list[Finding], *, as_of: str,
                   category: str | None = None) -> list[str]:
    """Phase 1 (deterministic): append each gated finding to its entity page, idempotently.
    Returns the sorted list of touched page ids."""
    _check_as_of_grain(as_of)
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
    exactly one 'ingest' log event per as_of (contradictions recorded in its detail, not yet weighted).

    F14 gate (before any write): every citation in a page's body must resolve to a gated finding,
    and every number in the body must trace to a cited finding (or the page's own state/trajectory).
    All pages are validated and all violations collected before raising, so nothing is written on
    a rejection."""
    _check_as_of_grain(as_of)
    violations: list[str] = []
    for pe in result.pages:
        violations.extend(_validate_enrichment_gate(store, pe))
    if violations:
        raise EnrichmentGateError(violations)

    contradictions: list[tuple[str, str]] = []
    for pe in result.pages:
        if not pe.pageId.startswith("entity:"):
            raise ValueError(f"enrichment targets non-entity page: {pe.pageId}")
        page = store.get_page(pe.pageId)  # raises PageNotFound (loud) if missing
        store.set_body(pe.pageId, pe.bodyMarkdown, as_of=as_of)  # idempotent
        salience = computed_salience(store, pe.pageId, as_of=as_of,
                                     contradiction=pe.contradictsThesis)
        if (page.state, page.trajectory, page.salience) != (pe.state, pe.trajectory, salience):
            store.record_state(pe.pageId, as_of=as_of, state=pe.state,
                               trajectory=pe.trajectory, salience=salience)
        if page.crossRefs != pe.crossRefs:
            store.update_header(pe.pageId, as_of=as_of, crossRefs=pe.crossRefs)
        if pe.contradictsThesis:
            contradictions.append((pe.pageId, pe.contradictionNote))
    detail = format_contradiction_detail(len(result.pages), contradictions)
    already_logged = any(e.kind == "ingest" and e.asOf == as_of and e.detail == detail
                         for e in store.log.read())
    if not already_logged:
        store.log.append(asOf=as_of, kind="ingest", detail=detail)
