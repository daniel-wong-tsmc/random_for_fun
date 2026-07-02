from __future__ import annotations
import json, pathlib

_VALID = {"demand", "supply"}

class TracksError(Exception):
    """A dimension has no anchor track, or a track value is invalid (fail loud)."""

class DimensionTracks:
    """Read accessor for the top-level `dimensionTracks` map in indicators.json (F9).
    The anchor polarity track is defined PER DIMENSION at registry level — never derived
    from finding order. Frozen IndicatorRegistry.load() ignores this key."""

    def __init__(self, mapping: dict[str, str]):
        self.mapping = mapping

    @classmethod
    def load(cls, path) -> "DimensionTracks":
        data = json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
        return cls(data.get("dimensionTracks", {}))

    def for_dimension(self, dimension: str) -> str:
        track = self.mapping.get(dimension)
        if track is None:
            raise TracksError(f"dimension '{dimension}' has no anchor track in dimensionTracks")
        if track not in _VALID:
            raise TracksError(f"dimension '{dimension}' has invalid track {track!r}")
        return track

    def validate(self, registry) -> None:
        """Every dimension used by a SCORING indicator must be mapped to a valid track."""
        violations: list[str] = []
        for ind_id in registry.indicators:
            spec = registry.resolve(ind_id)
            if not spec.scoring or spec.dimension is None:
                continue
            try:
                self.for_dimension(spec.dimension)
            except TracksError as e:
                violations.append(str(e))
        if violations:
            raise TracksError("; ".join(sorted(set(violations))))
