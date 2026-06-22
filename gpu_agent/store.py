from __future__ import annotations
import pathlib
from typing import Protocol
from gpu_agent.schema.scorecard import Scorecard

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
