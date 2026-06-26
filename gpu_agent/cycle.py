from __future__ import annotations
import pathlib
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
