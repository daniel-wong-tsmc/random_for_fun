from __future__ import annotations
import pathlib
from typing import Literal, Optional
from pydantic import BaseModel


class LogEvent(BaseModel):
    seq: int
    asOf: str
    kind: Literal["create-page", "append-observation", "state-change", "ingest", "query", "lint"]
    pageId: Optional[str] = None
    findingId: Optional[str] = None
    state: Optional[str] = None
    trajectory: Optional[str] = None
    salience: Optional[float] = None
    detail: str = ""


class Observation(BaseModel):
    asOf: str
    findingId: str


class StateChange(BaseModel):
    asOf: str
    state: str
    trajectory: str
    salience: float
    findingId: Optional[str] = None


class WikiLog:
    """Append-only JSONL event log. The temporal source of truth; no wall-clock."""

    def __init__(self, path: pathlib.Path):
        self.path = pathlib.Path(path)

    def read(self) -> list[LogEvent]:
        if not self.path.exists():
            return []
        out: list[LogEvent] = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line:
                out.append(LogEvent.model_validate_json(line))
        return out

    def append(self, *, asOf, kind, pageId=None, findingId=None, state=None,
               trajectory=None, salience=None, detail="") -> LogEvent:
        seq = len(self.read())  # deterministic, wall-clock-free
        event = LogEvent(seq=seq, asOf=asOf, kind=kind, pageId=pageId,
                         findingId=findingId, state=state, trajectory=trajectory,
                         salience=salience, detail=detail)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(event.model_dump_json() + "\n")
        return event

    def append_event(self, event: LogEvent) -> None:
        """Append a pre-built event (brain ingest/query/lint), re-stamping seq."""
        self.append(asOf=event.asOf, kind=event.kind, pageId=event.pageId,
                    findingId=event.findingId, state=event.state,
                    trajectory=event.trajectory, salience=event.salience,
                    detail=event.detail)
