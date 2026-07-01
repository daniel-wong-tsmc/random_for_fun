from __future__ import annotations
from typing import Optional
from pydantic import BaseModel, Field
import hashlib
import json
import pathlib
from gpu_agent.gathering.ingest import _normalize_url
from gpu_agent.schema.raw_document import RawDocument


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
        """Return (reason, firstSeenAsOf) if this doc is already known, else None. URL wins."""
        if url_norm in self._url:
            return ("seen-url", self._url[url_norm])
        if chash in self._hash:
            return ("seen-content-hash", self._hash[chash])
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
    """L1: drop documents already in the seen index (or repeated within this batch); record
    survivors. Returns (survivors, dropped) — nothing silent (every drop is a DroppedDoc)."""
    survivors: list[RawDocument] = []
    dropped: list[DroppedDoc] = []
    for doc in docs:
        url_norm = _normalize_url(doc.url)
        chash = content_hash(doc.content)
        hit = index.contains(url_norm, chash)
        if hit is not None:
            reason, first_seen = hit
            dropped.append(DroppedDoc(url=doc.url, reason=reason, firstSeenAsOf=first_seen))
            continue
        index.record(url_norm, chash, as_of)
        survivors.append(doc)
    return survivors, dropped
