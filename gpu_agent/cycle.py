from __future__ import annotations
import pathlib
from pydantic import BaseModel, Field
from gpu_agent.assignment import Assignment, load_assignment

class AssignmentProvider:
    """category_id -> its Assignment, by file convention `<root>/asg.<category_id>.json`.

    Returns None when no assignment exists (the caller logs it as skipped — Part 38
    no-silent-truncation). Swap this seam later for a taxonomy-default generator.
    """
    def __init__(self, root: str | pathlib.Path = "fixtures"):
        self.root = pathlib.Path(root)

    def path_for(self, category_id: str) -> pathlib.Path:
        return self.root / f"asg.{category_id}.json"

    def get(self, category_id: str) -> Assignment | None:
        p = self.path_for(category_id)
        if not p.exists():
            return None
        return load_assignment(p)


def resolve_scope(scope: str, taxonomy) -> tuple[str, ...]:
    if scope in ("all", "market"):
        return taxonomy.all_categories()
    if scope.startswith("category:"):
        cid = scope.split(":", 1)[1]
        if cid not in taxonomy.categories:
            raise ValueError(f"unknown category: {cid}")
        return (cid,)
    if scope.startswith("layer:"):
        return taxonomy.categories_in_layer(scope.split(":", 1)[1])
    raise ValueError(f"unrecognized scope: {scope!r} "
                     f"(expected 'category:<id>', 'layer:<id>', or 'all')")

class CycleEntry(BaseModel):
    category_id: str
    assignment_path: str | None
    status: str  # "ready" | "skipped-no-assignment"

class CyclePlan(BaseModel):
    scope: str
    entries: list[CycleEntry] = Field(default_factory=list)
    stages: list[dict[str, str]] = Field(default_factory=list)

def build_cycle_plan(scope: str, taxonomy, provider: AssignmentProvider) -> CyclePlan:
    entries: list[CycleEntry] = []
    for cid in resolve_scope(scope, taxonomy):
        path = provider.path_for(cid)
        if path.exists():
            entries.append(CycleEntry(category_id=cid, assignment_path=str(path), status="ready"))
        else:
            entries.append(CycleEntry(category_id=cid, assignment_path=None,
                                      status="skipped-no-assignment"))
    stages = [{"tier": "category", "status": "active"},
              {"tier": "layer", "status": "deferred"},
              {"tier": "main", "status": "deferred"}]
    return CyclePlan(scope=scope, entries=entries, stages=stages)
