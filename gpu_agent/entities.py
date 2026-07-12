"""F24 stage 1: canonical entity identity for NEW data. The single resolver over
docs/taxonomy.json `modularity.seedEntities` (consumed in place — no new registry file).
Known aliases (ticker, name variants, canonical id) resolve to the canonical id;
unregistered names return their slug form with registered=False and are NEVER rejected.
Deterministic: one cached taxonomy read, same input -> same output."""
from __future__ import annotations
import json
import pathlib
import re
from functools import lru_cache
from pydantic import BaseModel, Field

_SLUG_RE = re.compile(r"[^a-z0-9]+")


def _slug_key(name: str) -> str:
    """Slugified matching key: case-insensitive plus whitespace/punctuation-robust
    (same normalization rule as wiki.ingest.slug). Empty result fails loud."""
    s = _SLUG_RE.sub("-", name.strip().lower()).strip("-")
    if not s:
        raise ValueError(f"unresolvable entity (empty slug): {name!r}")
    return s


class SeedEntity(BaseModel):
    id: str
    name: str
    aliases: list[str] = Field(default_factory=list)
    primaryCategory: str
    appearsIn: list[str] = Field(default_factory=list)


class EntityResolver:
    def __init__(self, seeds: list[SeedEntity]):
        self._seeds_by_id: dict[str, SeedEntity] = {}
        self._alias_to_id: dict[str, str] = {}
        for seed in seeds:
            self._seeds_by_id[seed.id] = seed
            for variant in (seed.id, seed.name, *seed.aliases):
                key = _slug_key(variant)
                claimed = self._alias_to_id.get(key)
                if claimed is not None and claimed != seed.id:
                    raise ValueError(
                        f"entity alias collision: {variant!r} claimed by both "
                        f"'{claimed}' and '{seed.id}'")
                self._alias_to_id[key] = seed.id

    @classmethod
    def load(cls, path) -> "EntityResolver":
        data = json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
        raw = data.get("modularity", {}).get("seedEntities", [])
        return cls([SeedEntity.model_validate(e) for e in raw])

    def resolve(self, name: str) -> tuple[str, bool]:
        """(canonical_id, registered). Unregistered names return their slug form with
        False — pass-through, never a rejection (spec decision 2)."""
        key = _slug_key(name)
        canonical = self._alias_to_id.get(key)
        if canonical is not None:
            return canonical, True
        return key, False

    def display_name(self, name: str) -> str:
        canonical, registered = self.resolve(name)
        return self._seeds_by_id[canonical].name if registered else name

    def primary_category(self, name: str) -> str | None:
        canonical, registered = self.resolve(name)
        return self._seeds_by_id[canonical].primaryCategory if registered else None

    def appears_in(self, name: str) -> tuple[str, ...]:
        canonical, registered = self.resolve(name)
        return tuple(self._seeds_by_id[canonical].appearsIn) if registered else ()


@lru_cache(maxsize=1)
def default_resolver() -> EntityResolver:
    from gpu_agent.config import TAXONOMY_PATH
    return EntityResolver.load(TAXONOMY_PATH)
