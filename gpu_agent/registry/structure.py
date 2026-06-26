from __future__ import annotations
import json, pathlib
from pydantic import BaseModel, Field

class Taxonomy(BaseModel):
    dimensions: frozenset[str]
    categories: frozenset[str]
    categories_by_layer: dict[str, frozenset[str]] = Field(default_factory=dict)

    @classmethod
    def load(cls, path) -> "Taxonomy":
        data = json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
        dims = {d["id"] for d in data["scoringRubric"]["dimensions"]}
        by_layer = {
            layer["id"]: frozenset(f"{layer['id']}.{c['id']}" for c in layer["categories"])
            for layer in data["layers"]
        }
        cats = frozenset().union(*by_layer.values()) if by_layer else frozenset()
        return cls(dimensions=frozenset(dims), categories=cats, categories_by_layer=by_layer)

    def categories_in_layer(self, layer_id: str) -> tuple[str, ...]:
        if layer_id not in self.categories_by_layer:
            raise ValueError(f"unknown layer: {layer_id}")
        return tuple(sorted(self.categories_by_layer[layer_id]))

    def all_categories(self) -> tuple[str, ...]:
        return tuple(sorted(self.categories))
