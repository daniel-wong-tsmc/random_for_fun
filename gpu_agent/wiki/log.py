from __future__ import annotations
import pathlib
from typing import Literal, Optional
from pydantic import BaseModel


class LogEvent(BaseModel):
    seq: int
    asOf: str
    # NOTE (Lane E / F30, 2026-07-02): "header-change" added so store.update_header can log a
    # provenance event for lifecycle promotions/header edits. This is the one addition to
    # gpu_agent/wiki/log.py Lane E's plan (docs/superpowers/plans/2026-07-02-lane-e-wiki.md)
    # required outside its owned files: Task 4's spec requires update_header to append a
    # kind="header-change" LogEvent, and that value must round-trip through both write
    # (WikiLog.append) and read (LogEvent.model_validate_json) or the store cannot log it at
    # all. Purely additive (widens the allowed kind set by one string); no existing kind's
    # behavior changes.
    kind: Literal["create-page", "append-observation", "state-change", "ingest", "query", "lint",
                 "header-change"]
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
    """Append-only JSONL event log. The temporal source of truth; no wall-clock.

    F25: reads are served from an in-instance cache that is synced incrementally from a byte
    cursor - a `read()` only parses newly-appended bytes, never the whole file again. A per-page
    index (`events_for_page`) lets callers avoid scanning the full log per page. The on-disk
    format is unchanged; existing readers still work."""

    def __init__(self, path: pathlib.Path):
        self.path = pathlib.Path(path)
        self._events: list[LogEvent] = []
        self._by_page: dict[str, list[LogEvent]] = {}
        self._offset = 0                 # byte offset of the last complete line consumed
        self.parsed_lines = 0            # instrumentation: cumulative disk lines parsed

    def _reset(self) -> None:
        self._events = []
        self._by_page = {}
        self._offset = 0

    def _sync(self) -> None:
        """Pull any newly-appended complete lines from disk into the cache. O(new bytes); O(1)
        when nothing changed (the common case). Only complete newline-terminated lines are
        consumed, so a concurrent mid-write (a trailing partial line) is never mis-parsed."""
        try:
            size = self.path.stat().st_size
        except FileNotFoundError:
            if self._offset or self._events:
                self._reset()
            return
        if size == self._offset:
            return
        if size < self._offset:          # truncated / rebuilt / tmp reuse -> re-read from 0
            self._reset()
        with self.path.open("rb") as fh:
            fh.seek(self._offset)
            chunk = fh.read()
        nl = chunk.rfind(b"\n")
        if nl == -1:
            return                       # only a partial line so far
        complete = chunk[: nl + 1]
        for line in complete.decode("utf-8").split("\n"):
            if not line.strip():
                continue
            ev = LogEvent.model_validate_json(line)
            self._events.append(ev)
            if ev.pageId:
                self._by_page.setdefault(ev.pageId, []).append(ev)
            self.parsed_lines += 1
        self._offset += len(complete)

    def read(self) -> list[LogEvent]:
        self._sync()
        return self._events

    def events_for_page(self, page_id: str) -> list[LogEvent]:
        """All events for a page, in file order - O(events for that page), no full-log scan."""
        self._sync()
        return self._by_page.get(page_id, [])

    def count(self) -> int:
        self._sync()
        return len(self._events)

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
