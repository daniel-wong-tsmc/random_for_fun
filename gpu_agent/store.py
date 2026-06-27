from __future__ import annotations
import json
import pathlib
import re
from typing import Protocol
from gpu_agent.schema.scorecard import Scorecard
from gpu_agent.schema.finding import Finding

class Store(Protocol):
    """Pluggable persistence seam (spec §13.2) — swap JsonStore for SQLite later."""
    def append(self, sc: Scorecard) -> pathlib.Path: ...
    def versions(self, category_id: str, as_of: str) -> list[pathlib.Path]: ...

class JsonStore:
    def __init__(self, root: pathlib.Path):
        self.root = pathlib.Path(root)

    def versions(self, category_id: str, as_of: str) -> list[pathlib.Path]:
        d = self.root / category_id
        if not d.exists():
            return []
        return sorted(d.glob(f"{as_of}-v*.json"))

    def append(self, sc: Scorecard) -> pathlib.Path:
        d = self.root / sc.categoryId
        d.mkdir(parents=True, exist_ok=True)
        n = len(self.versions(sc.categoryId, sc.asOf)) + 1
        path = d / f"{sc.asOf}-v{n}.json"
        path.write_text(sc.model_dump_json(indent=2), encoding="utf-8")
        return path


_SAFE_ID = re.compile(r"^[A-Za-z0-9._-]+$")


class FindingNotFound(KeyError):
    """Raised when a finding id is not present in the FindingStore."""


class FindingStore:
    """Canonical, append-only store of gated Findings (Part 9). One file per id."""

    def __init__(self, root: pathlib.Path):
        self.root = pathlib.Path(root)

    def _path(self, finding_id: str) -> pathlib.Path:
        if not _SAFE_ID.match(finding_id):
            raise ValueError(f"unsafe finding id: {finding_id!r}")
        return self.root / f"{finding_id}.json"

    def append(self, finding: Finding) -> pathlib.Path:
        path = self._path(finding.id)
        payload = finding.model_dump_json(indent=2)
        if path.exists():
            existing = path.read_text(encoding="utf-8")
            if json.loads(existing) != json.loads(payload):
                raise ValueError(f"finding id collision with differing content: {finding.id}")
            return path  # immutable + idempotent: identical re-append is a no-op
        self.root.mkdir(parents=True, exist_ok=True)
        path.write_text(payload, encoding="utf-8")
        return path

    def get(self, finding_id: str) -> Finding:
        path = self._path(finding_id)
        if not path.exists():
            raise FindingNotFound(finding_id)
        return Finding.model_validate_json(path.read_text(encoding="utf-8"))

    def exists(self, finding_id: str) -> bool:
        try:
            return self._path(finding_id).exists()
        except ValueError:
            return False
