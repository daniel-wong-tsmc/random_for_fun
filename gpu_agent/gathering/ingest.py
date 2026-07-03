from __future__ import annotations
import hashlib
import re
from urllib.parse import urlparse
from pydantic import BaseModel, Field
from gpu_agent.schema.raw_document import RawDocument

REQUIRED: tuple[str, ...] = ("url", "content", "source", "date", "entity")

class Dropped(BaseModel):
    index: int
    url: str | None = None
    reason: str

class IngestOutcome(BaseModel):
    documents: list[RawDocument] = Field(default_factory=list)
    dropped: list[Dropped] = Field(default_factory=list)
    duplicates: int = 0

def _normalize_url(url: str) -> str:
    p = urlparse(url.strip())
    scheme = (p.scheme or "http").lower()
    netloc = p.netloc.lower()
    path = p.path.rstrip("/")
    query = f"?{p.query}" if p.query else ""   # keep query (distinct page), drop fragment
    return f"{scheme}://{netloc}{path}{query}"

def _host(url: str) -> str:
    return urlparse(url.strip()).netloc.lower()

def _tier(url: str, primary_sources: list[str]) -> str:
    host = _host(url)
    for src in primary_sources:
        s = src.strip().lower()
        if s and (host == s or host.endswith("." + s)):
            return "primary"
    return "secondary"

def _doc_id(normalized_url: str, as_of: str) -> str:
    host = urlparse(normalized_url).netloc.lower()
    slug = re.sub(r"[^a-z0-9]+", "-", host).strip("-") or "doc"
    digest = hashlib.sha256(normalized_url.encode("utf-8")).hexdigest()[:8]
    return f"{slug}-{digest}-{as_of}"   # F52: vintage-scoped — a re-gathered URL on a
                                        # later asOf is a NEW snapshot, so downstream
                                        # {docId}-{n} finding ids never collide cross-day

def normalize_documents(blobs: list[dict], *, primary_sources: list[str],
                        as_of: str) -> IngestOutcome:
    if not as_of.strip():
        raise ValueError("normalize_documents: as_of is required (F52 vintage-scoped ids)")
    documents: list[RawDocument] = []
    dropped: list[Dropped] = []
    duplicates = 0
    seen: set[str] = set()
    for i, blob in enumerate(blobs):
        missing = [k for k in REQUIRED if not str(blob.get(k, "")).strip()]
        if missing:
            dropped.append(Dropped(index=i, url=blob.get("url"),
                                   reason=f"missing/empty fields: {', '.join(missing)}"))
            continue
        norm = _normalize_url(blob["url"])
        if norm in seen:
            duplicates += 1
            continue
        seen.add(norm)
        documents.append(RawDocument(
            id=_doc_id(norm, as_of), source=blob["source"], url=blob["url"], date=blob["date"],
            tier=_tier(blob["url"], primary_sources), entity=blob["entity"], content=blob["content"]))
    return IngestOutcome(documents=documents, dropped=dropped, duplicates=duplicates)
