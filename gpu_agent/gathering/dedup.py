from __future__ import annotations
from typing import Optional
from urllib.parse import urlparse
from pydantic import BaseModel, Field
import hashlib
import json
import pathlib
from gpu_agent.gathering.ingest import _normalize_url
from gpu_agent.schema.raw_document import RawDocument
from gpu_agent.schema.finding import Finding
from gpu_agent.wiki.store import WikiStore, PageNotFound
from gpu_agent.wiki.ingest import slug


class DroppedDoc(BaseModel):
    url: str
    reason: str                    # "seen-url" | "seen-content-hash"
    firstSeenAsOf: str


class FindingClass(BaseModel):
    findingId: str
    entity: str
    indicatorId: str
    verdict: str                   # "new" | "update" | "duplicate"
    priorFindingId: Optional[str] = None
    detail: str = ""


class DedupResult(BaseModel):
    new: list[FindingClass] = Field(default_factory=list)
    update: list[FindingClass] = Field(default_factory=list)
    duplicate: list[FindingClass] = Field(default_factory=list)
    outFindings: list[Finding] = Field(default_factory=list)


class DedupReport(BaseModel):
    asOf: str
    docsDroppedKnown: list[DroppedDoc] = Field(default_factory=list)
    findingsNew: list[FindingClass] = Field(default_factory=list)
    findingsUpdate: list[FindingClass] = Field(default_factory=list)
    findingsDuplicate: list[FindingClass] = Field(default_factory=list)


class DedupConfig(BaseModel):
    rel_tol: float = 0.01          # relative tolerance for a measured-value change
    eps: float = 1e-9              # floor so a near-zero prior can't divide-by-zero


DEFAULT_DEDUP_CONFIG = DedupConfig()


def content_hash(content: str) -> str:
    """sha256 of the whitespace-folded content (so trivial reformatting still matches)."""
    folded = " ".join(content.split())
    return hashlib.sha256(folded.encode("utf-8")).hexdigest()


class SeenDocIndex:
    """Persistent, append-only cross-run memory of documents already ingested.
    Keyed by normalized URL AND content-hash -> first-seen asOf. Lives in the gitignored
    runtime store (e.g. store/seen_docs.jsonl)."""

    def __init__(self, path):
        self.path = pathlib.Path(path)
        self._url: dict[str, str] = {}     # url_norm -> firstSeenAsOf
        self._hash: dict[str, str] = {}     # content_hash -> firstSeenAsOf
        if self.path.exists():
            for line in self.path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line:
                    continue
                rec = json.loads(line)
                self._url.setdefault(rec["url"], rec["asOf"])
                self._hash.setdefault(rec["hash"], rec["asOf"])

    def contains(self, url_norm: str, chash: str):
        """Return (reason, firstSeenAsOf) if this doc is already known, else None.

        Known iff the CONTENT is known (F12: hash before URL — a stable URL whose
        content changed is a new document, not a seen one; stable price pages survive)."""
        if chash in self._hash:
            reason = "seen-url" if url_norm in self._url else "seen-content-hash"
            return (reason, self._hash[chash])
        return None

    def record(self, url_norm: str, chash: str, as_of: str) -> None:
        if url_norm in self._url and chash in self._hash:
            return
        self._url.setdefault(url_norm, as_of)
        self._hash.setdefault(chash, as_of)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps({"url": url_norm, "hash": chash, "asOf": as_of}) + "\n")


def filter_seen_documents(docs, index: SeenDocIndex, *, as_of):
    """L1 filter — PURE read against the index; recording is the caller's job AFTER the
    snapshots are durably written (F12: crash pre-write must not lose docs forever).
    Still drops batch-internal repeats by content hash. Returns (survivors, dropped) —
    nothing silent (every drop is a DroppedDoc)."""
    survivors: list[RawDocument] = []
    dropped: list[DroppedDoc] = []
    batch_hashes: set[str] = set()
    for doc in docs:
        url_norm = _normalize_url(doc.url)
        chash = content_hash(doc.content)
        hit = index.contains(url_norm, chash)
        if hit is None and chash in batch_hashes:
            hit = ("seen-content-hash", as_of)
        if hit is not None:
            reason, first_seen = hit
            dropped.append(DroppedDoc(url=doc.url, reason=reason, firstSeenAsOf=first_seen))
            continue
        batch_hashes.add(chash)
        survivors.append(doc)
    return survivors, dropped


def record_documents(docs, index: SeenDocIndex, *, as_of):
    """Record survivors as seen. Call ONLY after the docs' snapshots (and any batch log)
    are durably written to disk — a crash before that point must lose nothing forever."""
    for doc in docs:
        index.record(_normalize_url(doc.url), content_hash(doc.content), as_of)


def _norm_statement(s: str) -> str:
    return " ".join((s or "").split()).lower()


def prior_vintage(store, entity: str, indicator_id: str):
    """The store's latest-vintage Finding for (entity, indicatorId), read through the entity page's
    observations (FindingStore has no iteration). Latest by (capturedAt, observedAt, magnitude) —
    the same collapse the frozen dmi_smi_contribution uses. None if the page/indicator is absent."""
    pid = f"entity:{slug(entity)}"
    try:
        obs = store.observations(pid)
    except PageNotFound:
        return None
    cands = []
    for o in obs:
        try:
            f = store.findings.get(o.findingId)
        except Exception:
            continue
        if f.indicatorId == indicator_id:
            cands.append(f)
    if not cands:
        return None
    return max(cands, key=lambda f: (f.capturedAt, f.observedAt, f.magnitude))


def changed(prior, fresh, config=DEFAULT_DEDUP_CONFIG) -> bool:
    """UPDATE vs DUPLICATE. Measured: value delta beyond rel_tol OR magnitude change. Qualitative:
    a value appearing/disappearing, or a normalized-statement / trend / magnitude change."""
    pv = prior.value.number if prior.value is not None else None
    fv = fresh.value.number if fresh.value is not None else None
    if pv is not None and fv is not None:
        if abs(fv - pv) > config.rel_tol * max(abs(pv), config.eps):
            return True
        return fresh.magnitude != prior.magnitude
    if (pv is None) != (fv is None):
        return True  # a measured value appeared or disappeared
    return (_norm_statement(fresh.statement) != _norm_statement(prior.statement)
            or fresh.trend != prior.trend
            or fresh.magnitude != prior.magnitude)


def delta_detail(prior, fresh, config=DEFAULT_DEDUP_CONFIG) -> str:
    pv = prior.value.number if prior.value is not None else None
    fv = fresh.value.number if fresh.value is not None else None
    if pv is not None and fv is not None:
        return f"value {pv} -> {fv} (tol {config.rel_tol:.0%})"
    if fresh.magnitude != prior.magnitude:
        return f"magnitude {prior.magnitude} -> {fresh.magnitude}"
    return f"statement/trend changed (trend {prior.trend} -> {fresh.trend})"


def _price_publisher(f: Finding) -> str:
    """First evidence item's URL netloc, lowercased, minus a leading 'www.'; falls back to
    that evidence's source name, or '' when the finding carries no evidence at all (F51)."""
    if not f.evidence:
        return ""
    ev = f.evidence[0]
    netloc = urlparse(ev.url).netloc.lower()
    if netloc.startswith("www."):
        netloc = netloc[len("www."):]
    return netloc or ev.source.lower()


def _l2_key(f: Finding) -> tuple[str, str, str, str]:
    """F51: price findings ((f.side == 'price')) get a per-SERIES key — (entity, indicatorId,
    publisher, unit) — so different providers quoting the same entity+indicator (e.g. Lambda,
    CoreWeave, Runpod all reporting NVDA D6 rental price) land in separate series instead of
    colliding into one dispersed record. Non-price findings are unaffected: their key is still
    (entity, indicatorId), represented here as (entity, indicatorId, "", "") for a uniform tuple
    shape. KNOWN LIMIT: publisher+unit does not carry SKU — two SKUs at the SAME provider with
    the SAME unit (e.g. B200 vs H100 rental $/hr, both USD_per_gpu_hr) still collapse into one
    series until a dedicated seriesKey field exists (feature track)."""
    if f.side == "price":
        unit = f.value.unit if f.value else ""
        return (f.entity, f.indicatorId, _price_publisher(f), unit)
    return (f.entity, f.indicatorId, "", "")


def classify_findings(findings, store, *, config=DEFAULT_DEDUP_CONFIG) -> DedupResult:
    """L2: partition this cycle's gated findings into NEW / UPDATE / DUPLICATE vs the store's latest
    vintage per (entity, indicatorId) — or, for price findings, per (entity, indicatorId, publisher,
    unit) series (F51). Findings sharing a key are first collapsed to a representative (latest
    vintage tie-break). Batch-mates that AGREE with the representative (F10: corroboration)
    have their evidence merged into it instead of being silently discarded; batch-mates that CONFLICT
    set `dispersion` on the representative instead of being recency-collapsed away. Nothing silent."""
    by_key: dict[tuple[str, str, str, str], list] = {}
    for f in findings:
        by_key.setdefault(_l2_key(f), []).append(f)

    result = DedupResult()
    for (entity, ind, _publisher, _unit), group in sorted(by_key.items()):
        ordered = sorted(group, key=lambda f: (f.capturedAt, f.observedAt, f.magnitude), reverse=True)
        rep, superseded = ordered[0], ordered[1:]

        merged = rep
        for s in superseded:
            if not changed(s, rep, config):
                seen = {(e.source, e.url, e.date) for e in merged.evidence}
                extra = [e for e in s.evidence if (e.source, e.url, e.date) not in seen]
                if extra:
                    merged = merged.model_copy(update={"evidence": list(merged.evidence) + extra})
                result.duplicate.append(FindingClass(findingId=s.id, entity=entity, indicatorId=ind,
                                        verdict="duplicate", priorFindingId=rep.id,
                                        detail=f"corroborates {rep.id}; evidence merged"))
            else:
                merged = merged.model_copy(update={"dispersion":
                    f"conflicting same-key reports: {delta_detail(s, merged, config)}; "
                    f"sources: {', '.join(sorted({e.source for e in s.evidence} | {e.source for e in merged.evidence}))}"})
                result.duplicate.append(FindingClass(findingId=s.id, entity=entity, indicatorId=ind,
                                        verdict="duplicate",
                                        detail="superseded by intra-batch latest vintage"))

        prior = prior_vintage(store, entity, ind)
        if prior is None:
            result.new.append(FindingClass(findingId=merged.id, entity=entity, indicatorId=ind,
                                           verdict="new"))
            result.outFindings.append(merged)
        elif changed(prior, merged, config):
            result.update.append(FindingClass(findingId=merged.id, entity=entity, indicatorId=ind,
                                              verdict="update", priorFindingId=prior.id,
                                              detail=delta_detail(prior, merged, config)))
            result.outFindings.append(merged)
        else:
            result.duplicate.append(FindingClass(findingId=merged.id, entity=entity, indicatorId=ind,
                                                verdict="duplicate", priorFindingId=prior.id,
                                                detail="unchanged within tolerance"))
    return result
