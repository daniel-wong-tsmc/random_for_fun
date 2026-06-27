from __future__ import annotations
import pathlib
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

    # --- read ---
    def get_page(self, page_id) -> WikiPage:
        return self._read(page_id)[0]
