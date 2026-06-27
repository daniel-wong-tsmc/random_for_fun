from __future__ import annotations
import pathlib
from typing import Optional
from pydantic import BaseModel
from gpu_agent.schema.finding import Finding
from gpu_agent.wiki.page import WikiPage, dump_page, load_page
from gpu_agent.wiki.log import WikiLog, LogEvent, Observation, StateChange

_ALLOWED_HEADER_FIELDS = {"title", "category", "status", "crossRefs"}


class PageNotFound(KeyError):
    """Raised when a wiki page id is not present."""


class DuplicatePage(ValueError):
    """Raised when create_page targets an existing page."""


class FindingNotGated(ValueError):
    """Raised when append_observation references a finding absent from the FindingStore."""


class ResolvedObservation(BaseModel):
    asOf: str
    finding: Finding


class WindowView(BaseModel):
    page: WikiPage
    body: str
    observations: list[ResolvedObservation]


class IndexEntry(BaseModel):
    id: str
    type: str
    title: str
    category: Optional[str]
    status: str
    state: str
    trajectory: str
    salience: float
    lastUpdatedAsOf: str
    observationCount: int
    oneLine: str


class PageDelta(BaseModel):
    id: str
    title: str
    newFindingIds: list[str] = []
    stateTransition: Optional[dict] = None


class IndexMove(BaseModel):
    id: str
    oldState: str
    newState: str
    oldTrajectory: str
    newTrajectory: str
    oldSalience: float
    newSalience: float


class WikiDiff(BaseModel):
    new_pages: list[PageDelta] = []
    changed_pages: list[PageDelta] = []
    quiet_pages: list[str] = []
    index_moves: list[IndexMove] = []


class WikiStore:
    """LLM-wiki thread store: living markdown pages + an append-only log."""

    def __init__(self, root, finding_store):
        self.root = pathlib.Path(root)
        self.findings = finding_store
        self.log = WikiLog(self.root / "log.jsonl")

    # --- persistence helpers ---
    def _page_path(self, page_id: str) -> pathlib.Path:
        ptype, _, slug = page_id.partition(":")
        return self.root / ptype / f"{slug}.md"

    def _read(self, page_id: str) -> tuple[WikiPage, str]:
        path = self._page_path(page_id)
        if not path.exists():
            raise PageNotFound(page_id)
        return load_page(path.read_text(encoding="utf-8"))

    def _write(self, page: WikiPage, body: str) -> None:
        path = self._page_path(page.id)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(dump_page(page, body), encoding="utf-8")

    # --- mutate ---
    def create_page(self, id, type, title, category=None, *, as_of, body="") -> WikiPage:
        if self._page_path(id).exists():
            raise DuplicatePage(id)
        page = WikiPage(id=id, type=type, title=title, category=category,
                        createdAsOf=as_of, lastUpdatedAsOf=as_of)
        self._write(page, body)
        self.log.append(asOf=as_of, kind="create-page", pageId=id)
        return page

    def update_header(self, page_id, *, as_of, **fields) -> WikiPage:
        bad = set(fields) - _ALLOWED_HEADER_FIELDS
        if bad:
            raise ValueError(f"update_header: disallowed fields {sorted(bad)}")
        page, body = self._read(page_id)
        page = page.model_copy(update={**fields, "lastUpdatedAsOf": as_of})
        self._write(page, body)
        return page

    def append_observation(self, page_id, finding_id, *, as_of) -> WikiPage:
        page, body = self._read(page_id)
        if not self.findings.exists(finding_id):
            raise FindingNotGated(finding_id)
        page = page.model_copy(update={"lastUpdatedAsOf": as_of})
        self._write(page, body)
        self.log.append(asOf=as_of, kind="append-observation",
                        pageId=page_id, findingId=finding_id)
        return page

    def record_state(self, page_id, *, as_of, state, trajectory, salience, finding_id=None) -> WikiPage:
        page, body = self._read(page_id)
        page = page.model_copy(update={"state": state, "trajectory": trajectory,
                                       "salience": salience, "lastUpdatedAsOf": as_of})
        self._write(page, body)
        self.log.append(asOf=as_of, kind="state-change", pageId=page_id,
                        findingId=finding_id, state=state, trajectory=trajectory,
                        salience=salience)
        return page

    def log_append(self, event: LogEvent) -> None:
        self.log.append_event(event)

    def _events_for(self, page_id, kind) -> list[LogEvent]:
        evs = [e for e in self.log.read() if e.pageId == page_id and e.kind == kind]
        return sorted(evs, key=lambda e: (e.asOf, e.seq))

    def observations(self, page_id) -> list[Observation]:
        self._read(page_id)  # raises PageNotFound if absent
        return [Observation(asOf=e.asOf, findingId=e.findingId)
                for e in self._events_for(page_id, "append-observation")]

    def state_history(self, page_id) -> list[StateChange]:
        self._read(page_id)
        return [StateChange(asOf=e.asOf, state=e.state, trajectory=e.trajectory,
                            salience=e.salience, findingId=e.findingId)
                for e in self._events_for(page_id, "state-change")]

    def window(self, page_id, n) -> WindowView:
        page, body = self._read(page_id)
        all_obs = self.observations(page_id)
        recent = all_obs[-n:] if n > 0 else []
        resolved = [ResolvedObservation(asOf=o.asOf, finding=self.findings.get(o.findingId))
                    for o in recent]
        return WindowView(page=page, body=body, observations=resolved)

    def index(self) -> list[IndexEntry]:
        entries: list[IndexEntry] = []
        for ptype in ("entity", "theme"):
            d = self.root / ptype
            if not d.exists():
                continue
            for path in d.glob("*.md"):
                page, _ = load_page(path.read_text(encoding="utf-8"))
                count = len(self._events_for(page.id, "append-observation"))
                one = f"{page.title} — {page.state or 'no-state'} ({page.trajectory or 'n/a'})"
                entries.append(IndexEntry(
                    id=page.id, type=page.type, title=page.title, category=page.category,
                    status=page.status, state=page.state, trajectory=page.trajectory,
                    salience=page.salience, lastUpdatedAsOf=page.lastUpdatedAsOf,
                    observationCount=count, oneLine=one))
        return sorted(entries, key=lambda e: ((e.category or ""), e.id))

    def _state_at(self, events, on_or_before):
        sc = [e for e in events if e.kind == "state-change" and e.asOf <= on_or_before]
        if not sc:
            return None
        last = sorted(sc, key=lambda e: (e.asOf, e.seq))[-1]
        return {"state": last.state, "trajectory": last.trajectory, "salience": last.salience}

    def _title_or(self, page_id):
        try:
            return self.get_page(page_id).title
        except PageNotFound:
            return page_id

    def diff(self, as_of, prev_as_of) -> WikiDiff:
        by_page: dict[str, list] = {}
        for e in self.log.read():
            if e.pageId:
                by_page.setdefault(e.pageId, []).append(e)
        result = WikiDiff()
        for pid, evs in sorted(by_page.items()):
            evs = sorted(evs, key=lambda e: (e.asOf, e.seq))
            existed_now = any(e.asOf <= as_of for e in evs)
            if not existed_now:
                continue
            existed_prev = any(e.asOf <= prev_as_of for e in evs)
            window = [e for e in evs if prev_as_of < e.asOf <= as_of]
            new_findings = [e.findingId for e in window
                            if e.kind == "append-observation" and e.findingId]
            now_state = self._state_at(evs, as_of) or {}
            title = self._title_or(pid)
            if not existed_prev:
                trans = {"from": "", "to": now_state.get("state", "")} if now_state else None
                result.new_pages.append(PageDelta(id=pid, title=title,
                                                newFindingIds=new_findings, stateTransition=trans))
                continue
            if not window:
                result.quiet_pages.append(pid)
                continue
            prev_state = self._state_at(evs, prev_as_of) or {}
            trans = None
            if prev_state.get("state") != now_state.get("state"):
                trans = {"from": prev_state.get("state", ""), "to": now_state.get("state", "")}
            result.changed_pages.append(PageDelta(id=pid, title=title,
                                                newFindingIds=new_findings, stateTransition=trans))
            if prev_state != now_state and now_state:
                result.index_moves.append(IndexMove(
                    id=pid,
                    oldState=prev_state.get("state", ""), newState=now_state.get("state", ""),
                    oldTrajectory=prev_state.get("trajectory", ""), newTrajectory=now_state.get("trajectory", ""),
                    oldSalience=prev_state.get("salience", 0.0), newSalience=now_state.get("salience", 0.0)))
        result.index_moves.sort(key=lambda m: abs(m.newSalience - m.oldSalience), reverse=True)
        return result

    # --- read ---
    def get_page(self, page_id) -> WikiPage:
        return self._read(page_id)[0]
