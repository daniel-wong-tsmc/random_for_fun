from __future__ import annotations
import pathlib
from gpu_agent.wiki.page import WikiPage, dump_page, load_page
from gpu_agent.wiki.log import WikiLog

_ALLOWED_HEADER_FIELDS = {"title", "category", "status", "crossRefs"}


class PageNotFound(KeyError):
    """Raised when a wiki page id is not present."""


class DuplicatePage(ValueError):
    """Raised when create_page targets an existing page."""


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

    # --- read ---
    def get_page(self, page_id) -> WikiPage:
        return self._read(page_id)[0]
