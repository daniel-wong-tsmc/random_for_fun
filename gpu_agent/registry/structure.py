from __future__ import annotations
import json, pathlib
from pydantic import BaseModel

class Taxonomy(BaseModel):
    dimensions: frozenset[str]
    categories: frozenset[str]

    @classmethod
    def load(cls, path) -> "Taxonomy":
        data = json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
        dims = {d["id"] for d in data["scoringRubric"]["dimensions"]}
        cats = {f"{layer['id']}.{c['id']}"
                for layer in data["layers"] for c in layer["categories"]}
        return cls(dimensions=frozenset(dims), categories=frozenset(cats))
