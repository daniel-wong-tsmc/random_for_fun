from __future__ import annotations
import json, pathlib
from pydantic import BaseModel, Field

class Assignment(BaseModel):
    id: str
    template: str
    mode: str
    entities: list[str]
    metrics: list[str]
    weights: dict[str, float] = Field(default_factory=dict)
    version: str
    asOf: str

def load_assignment(path) -> Assignment:
    data = json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
    return Assignment.model_validate(data)
