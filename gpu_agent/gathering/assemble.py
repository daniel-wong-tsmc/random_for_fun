from __future__ import annotations

import json
import pathlib
from typing import Optional
from urllib.parse import urlparse

from pydantic import BaseModel, ValidationError


class GatherBlob(BaseModel):
    """F88: the reader-gatherer's per-page blob contract (mirrors the gather skill's step-3
    shape). Local to this module on purpose -- NOT a schema/ edit: this validates pre-ingest
    raw material written by reader agents that never touch the frozen scoring path; ids/tier
    are still stamped later by `ingest`'s normalize_documents, exactly as today."""

    source: str
    url: str
    date: str
    entity: str
    content: str
    chase: Optional[dict] = None
    originatingPublisher: Optional[str] = None


def _normalized_url(url: str) -> str:
    """Dedup key: lowercase scheme+host+path, trailing slash stripped. Deliberately narrower
    than `gathering.ingest._normalize_url` (which also keeps the query string) -- this is the
    assembler's own duplicate-detection rule, per the F88 Task 4 spec, not the ingest tier's."""
    p = urlparse(url.strip())
    scheme = p.scheme.lower()
    host = p.netloc.lower()
    path = p.path.rstrip("/")
    return f"{scheme}://{host}{path}"


def _validation_reason(exc: ValidationError) -> str:
    fields = sorted({str(err["loc"][0]) for err in exc.errors() if err.get("loc")})
    if fields:
        return f"schema-invalid: {', '.join(fields)}"
    return "schema-invalid"


def _read_rounds(blob_dir: pathlib.Path) -> int:
    rounds_path = blob_dir / "rounds.txt"
    if not rounds_path.exists():
        return 1
    try:
        return int(rounds_path.read_text(encoding="utf-8").strip())
    except (OSError, ValueError):
        return 1


def assemble(blob_dir: pathlib.Path) -> dict:
    """Deterministically turn a directory of reader-gatherer blob files into the single
    `blobs.json` envelope `ingest --blobs` already accepts ({"rounds","skipped","blobs"}).
    Never raises on a bad blob file -- malformed JSON or a GatherBlob-invalid file is
    recorded as a `skipped` row and assembly continues. A duplicate normalized URL within
    the directory skips the LATER file (by sorted filename), keeping the earlier one.
    The same directory assembles byte-identically on every call: blobs are read in
    filename order and the kept set is re-sorted by (normalized url, filename) before
    being emitted, so read order and glob order never leak into the output."""
    blob_dir = pathlib.Path(blob_dir)
    skipped: list[dict] = []
    kept: list[tuple[str, str, GatherBlob]] = []
    seen_urls: set[str] = set()

    for path in sorted(blob_dir.glob("*.json"), key=lambda p: p.name):
        name = path.name
        try:
            raw = path.read_text(encoding="utf-8")
        except OSError as e:
            skipped.append({"path": name, "reason": f"unreadable: {e}"})
            continue
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as e:
            skipped.append({"path": name, "reason": f"malformed JSON: {e}"})
            continue
        try:
            blob = GatherBlob.model_validate(data)
        except ValidationError as e:
            skipped.append({"path": name, "reason": _validation_reason(e)})
            continue
        norm = _normalized_url(blob.url)
        if norm in seen_urls:
            skipped.append({"path": name, "reason": "duplicate-url"})
            continue
        seen_urls.add(norm)
        kept.append((norm, name, blob))

    kept.sort(key=lambda t: (t[0], t[1]))
    blobs = [blob.model_dump(exclude_none=True) for _, _, blob in kept]

    return {"rounds": _read_rounds(blob_dir), "skipped": skipped, "blobs": blobs}
