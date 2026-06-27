# Temporal store + LLM-wiki thread model (sub-project 4-1) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the keystone temporal store for the daily monitor — a standalone append-only `FindingStore` and an LLM-wiki `WikiStore` (entity/theme threads as living markdown pages, an append-only `log.jsonl`, a computed `index`, and `diff(as_of, prev_as_of)`) — as pure, deterministic code.

**Architecture:** Findings are stored once in `FindingStore` (`store/findings/<id>.json`) and referenced by id. Wiki threads are markdown files (`store/wiki/<type>/<slug>.md`) with a no-dependency `key: <json>` frontmatter header + a brain-curated body; the append-only `store/wiki/log.jsonl` is the temporal source of truth, and `observations` / `state_history` / `window` / `diff` are derived from it. Everything is additive — no frozen file is touched.

**Tech Stack:** Python 3.11+, Pydantic v2 (the only runtime dependency), stdlib `json`/`pathlib`/`re`, pytest.

## Global Constraints

- **Run from repo root** `C:\Users\danie\random_for_fun`; interpreter `.venv/Scripts/python`. CWD can reset — prefix commands with `cd /c/Users/danie/random_for_fun &&`.
- **No new dependency.** Runtime deps stay exactly `["pydantic>=2,<3"]`. No PyYAML, no others. Frontmatter uses stdlib `json` only.
- **Truly frozen — byte-unchanged:** `gpu_agent/gate.py`, `gpu_agent/scoring.py`, `gpu_agent/registry/indicators.py`, `gpu_agent/registry/validate.py`, the `Finding` schema (`gpu_agent/schema/finding.py`), the 6 dimension names, the rating scale, `pipeline.py`'s Part-7 gate, and the existing `JsonStore` class body in `store.py`. **Additive only** (Part 33): new `FindingStore` in `store.py`, new `gpu_agent/wiki/` package.
- **Determinism:** no wall-clock anywhere. `asOf` (a `YYYY-MM-DD` string) is always passed in; log ordering is `(asOf, seq)` where `seq` is the line count at append time.
- **Doctrine:** code computes + gates + stores; `append_observation` refuses an ungated finding; malformed files and id collisions **fail loud** (never a silent half-parse).
- **The full suite stays green after every task.** Baseline: **211 passed, 3 skipped**. Run `.venv/Scripts/python -m pytest -q` before each commit.
- **Every commit message ends with:** `Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>`

---

### Task 1: `FindingStore` — canonical append-only finding store

**Files:**
- Modify: `gpu_agent/store.py` (add `FindingStore` + `FindingNotFound`; leave `Store`/`JsonStore` untouched)
- Test: `tests/test_finding_store.py`

**Interfaces:**
- Consumes: `gpu_agent.schema.finding.Finding` (frozen schema).
- Produces:
  - `class FindingNotFound(KeyError)`
  - `class FindingStore:` with `__init__(self, root: pathlib.Path)`, `append(self, finding: Finding) -> pathlib.Path` (write-if-absent; identical re-append = no-op; id collision with differing content raises `ValueError`), `get(self, finding_id: str) -> Finding` (raises `FindingNotFound`), `exists(self, finding_id: str) -> bool`. Unsafe ids (not matching `^[A-Za-z0-9._-]+$`) raise `ValueError` in `get`/`append`; `exists` returns `False` for them.

- [ ] **Step 1: Write the failing test**

Create `tests/test_finding_store.py`:

```python
import pytest
from gpu_agent.store import FindingStore, FindingNotFound
from gpu_agent.schema.finding import Finding, Kind, Impact, Confidence


def _finding(fid="f-2026-06-26-001", statement="CoWoS capacity tight"):
    return Finding(
        id=fid, statement=statement, kind=Kind.observed, trend="flat",
        why="capacity constraint",
        impact=Impact(targets=["nvidia"], direction="negative", mechanism="supply limit"),
        confidence=Confidence(level="medium", basis="single secondary source"),
        asOf="2026-06-26", indicatorId="cowosCapacity", side="supply",
        polarityDemand=0, polaritySupply=-1, magnitude=2, entity="tsmc",
        observedAt="2026-06-26", capturedAt="2026-06-26",
    )


def test_append_then_get_roundtrips(tmp_path):
    store = FindingStore(tmp_path)
    store.append(_finding())
    got = store.get("f-2026-06-26-001")
    assert got.statement == "CoWoS capacity tight"
    assert got.polaritySupply == -1


def test_exists(tmp_path):
    store = FindingStore(tmp_path)
    assert not store.exists("f-x")
    store.append(_finding(fid="f-x"))
    assert store.exists("f-x")


def test_get_missing_raises(tmp_path):
    store = FindingStore(tmp_path)
    with pytest.raises(FindingNotFound):
        store.get("nope")


def test_append_is_idempotent_for_identical(tmp_path):
    store = FindingStore(tmp_path)
    p1 = store.append(_finding())
    p2 = store.append(_finding())  # identical → no-op
    assert p1 == p2


def test_append_collision_with_different_content_raises(tmp_path):
    store = FindingStore(tmp_path)
    store.append(_finding(statement="A"))
    with pytest.raises(ValueError):
        store.append(_finding(statement="B"))  # same id, different content


def test_unsafe_id_rejected(tmp_path):
    store = FindingStore(tmp_path)
    with pytest.raises(ValueError):
        store.get("../etc/passwd")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /c/Users/danie/random_for_fun && .venv/Scripts/python -m pytest tests/test_finding_store.py -q`
Expected: FAIL with `ImportError: cannot import name 'FindingStore'`.

- [ ] **Step 3: Write minimal implementation**

In `gpu_agent/store.py`, add at the top with the other imports:

```python
import json
import re
from gpu_agent.schema.finding import Finding
```

Then append to the end of the file:

```python
_SAFE_ID = re.compile(r"^[A-Za-z0-9._-]+$")


class FindingNotFound(KeyError):
    """Raised when a finding id is not present in the FindingStore."""


class FindingStore:
    """Canonical, append-only store of gated Findings (Part 9). One file per id."""

    def __init__(self, root: pathlib.Path):
        self.root = pathlib.Path(root)

    def _path(self, finding_id: str) -> pathlib.Path:
        if not _SAFE_ID.match(finding_id):
            raise ValueError(f"unsafe finding id: {finding_id!r}")
        return self.root / f"{finding_id}.json"

    def append(self, finding: Finding) -> pathlib.Path:
        path = self._path(finding.id)
        payload = finding.model_dump_json(indent=2)
        if path.exists():
            existing = path.read_text(encoding="utf-8")
            if json.loads(existing) != json.loads(payload):
                raise ValueError(f"finding id collision with differing content: {finding.id}")
            return path  # immutable + idempotent: identical re-append is a no-op
        self.root.mkdir(parents=True, exist_ok=True)
        path.write_text(payload, encoding="utf-8")
        return path

    def get(self, finding_id: str) -> Finding:
        path = self._path(finding_id)
        if not path.exists():
            raise FindingNotFound(finding_id)
        return Finding.model_validate_json(path.read_text(encoding="utf-8"))

    def exists(self, finding_id: str) -> bool:
        try:
            return self._path(finding_id).exists()
        except ValueError:
            return False
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /c/Users/danie/random_for_fun && .venv/Scripts/python -m pytest tests/test_finding_store.py -q`
Expected: PASS (6 passed).

- [ ] **Step 5: Run the full suite**

Run: `cd /c/Users/danie/random_for_fun && .venv/Scripts/python -m pytest -q`
Expected: 217 passed, 3 skipped (211 baseline + 6 new).

- [ ] **Step 6: Commit**

```bash
cd /c/Users/danie/random_for_fun && git add gpu_agent/store.py tests/test_finding_store.py && git commit -m "feat(4-1): FindingStore — canonical append-only gated-finding store

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 2: `WikiPage` + the no-dependency frontmatter serializer

**Files:**
- Create: `gpu_agent/wiki/__init__.py` (empty package marker)
- Create: `gpu_agent/wiki/page.py`
- Test: `tests/test_wiki_page.py`

**Interfaces:**
- Produces:
  - `class WikiFormatError(ValueError)`
  - `class WikiPage(BaseModel)` with fields: `id: str`, `type: Literal["entity","theme"]`, `title: str`, `category: Optional[str] = None`, `status: Literal["provisional","registered"] = "provisional"`, `state: str = ""`, `trajectory: str = ""`, `salience: float = 0.0`, `crossRefs: list[str] = []`, `createdAsOf: str`, `lastUpdatedAsOf: str`.
  - `def dump_page(page: WikiPage, body: str) -> str`
  - `def load_page(text: str) -> tuple[WikiPage, str]` (raises `WikiFormatError` on a malformed file)

- [ ] **Step 1: Write the failing test**

Create `tests/test_wiki_page.py`:

```python
import pytest
from gpu_agent.wiki.page import WikiPage, dump_page, load_page, WikiFormatError


def _page():
    return WikiPage(
        id="theme:cowos-capacity", type="theme", title="CoWoS capacity",
        category="chips.merchant-gpu", state="slipping",
        trajectory="on-track -> slipping", salience=0.8,
        crossRefs=["theme:hbm4", "entity:tsmc"],
        createdAsOf="2026-06-20", lastUpdatedAsOf="2026-06-27",
    )


def test_roundtrip_preserves_header_and_body():
    page = _page()
    body = "## CoWoS\nTSMC slipping [f-1].\n"
    text = dump_page(page, body)
    p2, b2 = load_page(text)
    assert p2 == page
    assert b2 == body
    assert isinstance(p2.salience, float) and p2.salience == 0.8


def test_defaults_roundtrip():
    page = WikiPage(id="entity:nvidia", type="entity", title="NVIDIA",
                    createdAsOf="2026-06-26", lastUpdatedAsOf="2026-06-26")
    p2, b2 = load_page(dump_page(page, ""))
    assert p2 == page and p2.category is None and p2.status == "provisional"


def test_body_with_triple_dash_survives():
    page = _page()
    body = "intro\n---\na horizontal rule in the body\n"
    p2, b2 = load_page(dump_page(page, body))
    assert b2 == body


def test_missing_opening_fence_raises():
    with pytest.raises(WikiFormatError):
        load_page('id: "x"\n')


def test_missing_closing_fence_raises():
    with pytest.raises(WikiFormatError):
        load_page('---\nid: "theme:x"\n')


def test_non_json_value_raises():
    with pytest.raises(WikiFormatError):
        load_page('---\nid: not-json-unquoted\n---\nbody')
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /c/Users/danie/random_for_fun && .venv/Scripts/python -m pytest tests/test_wiki_page.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'gpu_agent.wiki'`.

- [ ] **Step 3: Write minimal implementation**

Create `gpu_agent/wiki/__init__.py` (empty file).

Create `gpu_agent/wiki/page.py`:

```python
from __future__ import annotations
import json
from typing import Literal, Optional
from pydantic import BaseModel, Field


class WikiFormatError(ValueError):
    """Raised when a wiki page file cannot be parsed (fail loud, never half-parse)."""


class WikiPage(BaseModel):
    """The code-owned frontmatter header of a wiki thread (the body is stored separately)."""
    id: str
    type: Literal["entity", "theme"]
    title: str
    category: Optional[str] = None
    status: Literal["provisional", "registered"] = "provisional"
    state: str = ""
    trajectory: str = ""
    salience: float = 0.0
    crossRefs: list[str] = Field(default_factory=list)
    createdAsOf: str
    lastUpdatedAsOf: str


def dump_page(page: WikiPage, body: str) -> str:
    """Serialize to '---\\n<key: json-value lines>\\n---\\n<body>'. JSON is a YAML-flow subset."""
    lines = ["---"]
    for key, value in page.model_dump().items():
        lines.append(f"{key}: {json.dumps(value)}")
    lines.append("---")
    return "\n".join(lines) + "\n" + body


def load_page(text: str) -> tuple[WikiPage, str]:
    if not text.startswith("---\n"):
        raise WikiFormatError("missing opening frontmatter fence")
    parts = text.split("---\n", 2)  # first two fences only; a body '---' survives
    if len(parts) < 3:
        raise WikiFormatError("missing closing frontmatter fence")
    _, frontmatter, body = parts
    header: dict = {}
    for line in frontmatter.splitlines():
        if not line.strip():
            continue
        key, sep, rest = line.partition(": ")
        if not sep:
            raise WikiFormatError(f"malformed frontmatter line: {line!r}")
        try:
            header[key] = json.loads(rest)
        except json.JSONDecodeError as exc:
            raise WikiFormatError(f"non-JSON frontmatter value for {key!r}: {rest!r}") from exc
    try:
        return WikiPage(**header), body
    except Exception as exc:  # pydantic ValidationError → uniform WikiFormatError
        raise WikiFormatError(f"invalid page header: {exc}") from exc
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /c/Users/danie/random_for_fun && .venv/Scripts/python -m pytest tests/test_wiki_page.py -q`
Expected: PASS (6 passed).

- [ ] **Step 5: Run the full suite**

Run: `cd /c/Users/danie/random_for_fun && .venv/Scripts/python -m pytest -q`
Expected: 223 passed, 3 skipped.

- [ ] **Step 6: Commit**

```bash
cd /c/Users/danie/random_for_fun && git add gpu_agent/wiki/__init__.py gpu_agent/wiki/page.py tests/test_wiki_page.py && git commit -m "feat(4-1): WikiPage + no-dependency key:<json> frontmatter serializer

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 3: `LogEvent` + `WikiLog` — the append-only temporal source of truth

**Files:**
- Create: `gpu_agent/wiki/log.py`
- Test: `tests/test_wiki_log.py`

**Interfaces:**
- Produces:
  - `class LogEvent(BaseModel)`: `seq: int`, `asOf: str`, `kind: Literal["create-page","append-observation","state-change","ingest","query","lint"]`, `pageId: Optional[str]=None`, `findingId: Optional[str]=None`, `state: Optional[str]=None`, `trajectory: Optional[str]=None`, `salience: Optional[float]=None`, `detail: str=""`.
  - `class Observation(BaseModel)`: `asOf: str`, `findingId: str`.
  - `class StateChange(BaseModel)`: `asOf: str`, `state: str`, `trajectory: str`, `salience: float`, `findingId: Optional[str]=None`.
  - `class WikiLog`: `__init__(self, path)`, `read(self) -> list[LogEvent]` (missing file → `[]`), `append(self, *, asOf, kind, pageId=None, findingId=None, state=None, trajectory=None, salience=None, detail="") -> LogEvent` (assigns `seq = len(self.read())`), `append_event(self, event: LogEvent) -> None` (re-stamps seq for pre-built brain events).

- [ ] **Step 1: Write the failing test**

Create `tests/test_wiki_log.py`:

```python
from gpu_agent.wiki.log import WikiLog, LogEvent


def test_append_assigns_monotonic_seq(tmp_path):
    log = WikiLog(tmp_path / "log.jsonl")
    e0 = log.append(asOf="2026-06-26", kind="create-page", pageId="theme:x")
    e1 = log.append(asOf="2026-06-26", kind="append-observation", pageId="theme:x", findingId="f-1")
    assert e0.seq == 0 and e1.seq == 1


def test_read_returns_all_events_in_order(tmp_path):
    log = WikiLog(tmp_path / "log.jsonl")
    log.append(asOf="2026-06-26", kind="create-page", pageId="theme:x")
    log.append(asOf="2026-06-27", kind="state-change", pageId="theme:x",
               state="slipping", trajectory="t", salience=0.5)
    evs = log.read()
    assert [e.kind for e in evs] == ["create-page", "state-change"]
    assert evs[1].salience == 0.5


def test_read_missing_file_is_empty(tmp_path):
    assert WikiLog(tmp_path / "none.jsonl").read() == []


def test_append_event_restamps_seq(tmp_path):
    log = WikiLog(tmp_path / "log.jsonl")
    log.append(asOf="2026-06-26", kind="create-page", pageId="p")
    log.append_event(LogEvent(seq=999, asOf="2026-06-27", kind="ingest", detail="brain"))
    evs = log.read()
    assert evs[-1].seq == 1 and evs[-1].kind == "ingest" and evs[-1].detail == "brain"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /c/Users/danie/random_for_fun && .venv/Scripts/python -m pytest tests/test_wiki_log.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'gpu_agent.wiki.log'`.

- [ ] **Step 3: Write minimal implementation**

Create `gpu_agent/wiki/log.py`:

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /c/Users/danie/random_for_fun && .venv/Scripts/python -m pytest tests/test_wiki_log.py -q`
Expected: PASS (4 passed).

- [ ] **Step 5: Run the full suite**

Run: `cd /c/Users/danie/random_for_fun && .venv/Scripts/python -m pytest -q`
Expected: 227 passed, 3 skipped.

- [ ] **Step 6: Commit**

```bash
cd /c/Users/danie/random_for_fun && git add gpu_agent/wiki/log.py tests/test_wiki_log.py && git commit -m "feat(4-1): WikiLog + LogEvent — append-only deterministic temporal log

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 4: `WikiStore` core — create / get / update_header + page persistence

**Files:**
- Create: `gpu_agent/wiki/store.py`
- Test: `tests/test_wiki_store.py`

**Interfaces:**
- Consumes: `FindingStore` (Task 1); `WikiPage`/`dump_page`/`load_page` (Task 2); `WikiLog` (Task 3).
- Produces:
  - `class PageNotFound(KeyError)`, `class DuplicatePage(ValueError)`
  - `class WikiStore`: `__init__(self, root, finding_store)` (creates `self.log = WikiLog(root/"log.jsonl")`, `self.findings = finding_store`); `create_page(self, id, type, title, category=None, *, as_of, body="") -> WikiPage` (raises `DuplicatePage`; logs `create-page`); `get_page(self, page_id) -> WikiPage` (raises `PageNotFound`); `update_header(self, page_id, *, as_of, **fields) -> WikiPage` (only `title`/`category`/`status`/`crossRefs`; other fields raise `ValueError`; bumps `lastUpdatedAsOf`; no log event). Page files live at `root/<type>/<slug>.md` where `id == "<type>:<slug>"`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_wiki_store.py`:

```python
import pytest
from gpu_agent.store import FindingStore
from gpu_agent.wiki.store import WikiStore, PageNotFound, DuplicatePage


def _store(tmp_path):
    return WikiStore(tmp_path / "wiki", FindingStore(tmp_path / "findings"))


def test_create_then_get(tmp_path):
    ws = _store(tmp_path)
    ws.create_page("theme:cowos", "theme", "CoWoS", category="chips.merchant-gpu", as_of="2026-06-26")
    page = ws.get_page("theme:cowos")
    assert page.title == "CoWoS" and page.status == "provisional"
    assert page.createdAsOf == "2026-06-26" and page.lastUpdatedAsOf == "2026-06-26"


def test_create_writes_file_at_typed_path(tmp_path):
    ws = _store(tmp_path)
    ws.create_page("entity:nvidia", "entity", "NVIDIA", as_of="2026-06-26")
    assert (tmp_path / "wiki" / "entity" / "nvidia.md").exists()


def test_create_duplicate_raises(tmp_path):
    ws = _store(tmp_path)
    ws.create_page("theme:cowos", "theme", "CoWoS", as_of="2026-06-26")
    with pytest.raises(DuplicatePage):
        ws.create_page("theme:cowos", "theme", "CoWoS", as_of="2026-06-27")


def test_get_missing_raises(tmp_path):
    ws = _store(tmp_path)
    with pytest.raises(PageNotFound):
        ws.get_page("theme:nope")


def test_create_logs_event(tmp_path):
    ws = _store(tmp_path)
    ws.create_page("theme:cowos", "theme", "CoWoS", as_of="2026-06-26")
    evs = ws.log.read()
    assert evs[0].kind == "create-page" and evs[0].pageId == "theme:cowos"


def test_update_header_allowed_fields(tmp_path):
    ws = _store(tmp_path)
    ws.create_page("theme:cowos", "theme", "CoWoS", as_of="2026-06-26")
    ws.update_header("theme:cowos", as_of="2026-06-28", status="registered", crossRefs=["entity:tsmc"])
    page = ws.get_page("theme:cowos")
    assert page.status == "registered" and page.crossRefs == ["entity:tsmc"]
    assert page.lastUpdatedAsOf == "2026-06-28"


def test_update_header_disallowed_field_raises(tmp_path):
    ws = _store(tmp_path)
    ws.create_page("theme:cowos", "theme", "CoWoS", as_of="2026-06-26")
    with pytest.raises(ValueError):
        ws.update_header("theme:cowos", as_of="2026-06-28", salience=0.9)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /c/Users/danie/random_for_fun && .venv/Scripts/python -m pytest tests/test_wiki_store.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'gpu_agent.wiki.store'`.

- [ ] **Step 3: Write minimal implementation**

Create `gpu_agent/wiki/store.py`:

```python
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
        for key, value in fields.items():
            setattr(page, key, value)
        page.lastUpdatedAsOf = as_of
        self._write(page, body)
        return page

    # --- read ---
    def get_page(self, page_id) -> WikiPage:
        return self._read(page_id)[0]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /c/Users/danie/random_for_fun && .venv/Scripts/python -m pytest tests/test_wiki_store.py -q`
Expected: PASS (7 passed).

- [ ] **Step 5: Run the full suite**

Run: `cd /c/Users/danie/random_for_fun && .venv/Scripts/python -m pytest -q`
Expected: 234 passed, 3 skipped.

- [ ] **Step 6: Commit**

```bash
cd /c/Users/danie/random_for_fun && git add gpu_agent/wiki/store.py tests/test_wiki_store.py && git commit -m "feat(4-1): WikiStore core — create/get/update_header + page persistence

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 5: `WikiStore` observations — append_observation / record_state / window

**Files:**
- Modify: `gpu_agent/wiki/store.py` (add the observation/state methods + result types)
- Test: `tests/test_wiki_observations.py`

**Interfaces:**
- Consumes: the Task 4 `WikiStore` (`self.findings`, `self.log`, `self._read`, `self._write`); `Observation`/`StateChange` (Task 3); `FindingStore.exists`/`.get` (Task 1); `Finding` schema.
- Produces (added to `WikiStore`):
  - `class FindingNotGated(ValueError)` (module-level)
  - `class ResolvedObservation(BaseModel)`: `asOf: str`, `finding: Finding`
  - `class WindowView(BaseModel)`: `page: WikiPage`, `body: str`, `observations: list[ResolvedObservation]`
  - `append_observation(self, page_id, finding_id, *, as_of) -> WikiPage` (raises `PageNotFound` if no page, `FindingNotGated` if `finding_id` not in `FindingStore`; logs `append-observation`; bumps `lastUpdatedAsOf`)
  - `record_state(self, page_id, *, as_of, state, trajectory, salience, finding_id=None) -> WikiPage` (syncs cached `state`/`trajectory`/`salience`; logs `state-change`)
  - `log_append(self, event) -> None` (delegates to `self.log.append_event`)
  - `observations(self, page_id) -> list[Observation]` (derived from log, ordered `(asOf, seq)`; raises `PageNotFound`)
  - `state_history(self, page_id) -> list[StateChange]`
  - `window(self, page_id, n) -> WindowView` (last-n observations resolved via `FindingStore`)
  - helper `_events_for(self, page_id, kind) -> list[LogEvent]`

- [ ] **Step 1: Write the failing test**

Create `tests/test_wiki_observations.py`:

```python
import pytest
from gpu_agent.store import FindingStore
from gpu_agent.wiki.store import WikiStore, FindingNotGated
from gpu_agent.schema.finding import Finding, Kind, Impact, Confidence


def _finding(fid):
    return Finding(
        id=fid, statement="s", kind=Kind.observed, trend="flat", why="w",
        impact=Impact(targets=["nvidia"], direction="negative", mechanism="m"),
        confidence=Confidence(level="medium", basis="b"), asOf="2026-06-26",
        indicatorId="cowosCapacity", side="supply", polarityDemand=0, polaritySupply=-1,
        magnitude=2, entity="tsmc", observedAt="2026-06-26", capturedAt="2026-06-26",
    )


def _store(tmp_path):
    fs = FindingStore(tmp_path / "findings")
    return WikiStore(tmp_path / "wiki", fs), fs


def test_append_observation_requires_gated_finding(tmp_path):
    ws, fs = _store(tmp_path)
    ws.create_page("theme:cowos", "theme", "CoWoS", as_of="2026-06-26")
    with pytest.raises(FindingNotGated):
        ws.append_observation("theme:cowos", "f-missing", as_of="2026-06-26")


def test_append_observation_records_and_logs(tmp_path):
    ws, fs = _store(tmp_path)
    fs.append(_finding("f-1"))
    ws.create_page("theme:cowos", "theme", "CoWoS", as_of="2026-06-26")
    ws.append_observation("theme:cowos", "f-1", as_of="2026-06-27")
    obs = ws.observations("theme:cowos")
    assert [o.findingId for o in obs] == ["f-1"]
    assert ws.get_page("theme:cowos").lastUpdatedAsOf == "2026-06-27"


def test_record_state_updates_cache_and_history(tmp_path):
    ws, fs = _store(tmp_path)
    ws.create_page("theme:cowos", "theme", "CoWoS", as_of="2026-06-26")
    ws.record_state("theme:cowos", as_of="2026-06-27", state="slipping",
                    trajectory="on-track -> slipping", salience=0.8)
    page = ws.get_page("theme:cowos")
    assert page.state == "slipping" and page.salience == 0.8
    hist = ws.state_history("theme:cowos")
    assert len(hist) == 1 and hist[0].state == "slipping"


def test_window_resolves_last_n_findings(tmp_path):
    ws, fs = _store(tmp_path)
    for i in (1, 2, 3):
        fs.append(_finding(f"f-{i}"))
    ws.create_page("theme:cowos", "theme", "CoWoS", as_of="2026-06-26")
    ws.append_observation("theme:cowos", "f-1", as_of="2026-06-26")
    ws.append_observation("theme:cowos", "f-2", as_of="2026-06-27")
    ws.append_observation("theme:cowos", "f-3", as_of="2026-06-28")
    win = ws.window("theme:cowos", 2)
    assert [o.finding.id for o in win.observations] == ["f-2", "f-3"]
    assert win.page.id == "theme:cowos"


def test_observations_on_missing_page_raises(tmp_path):
    ws, fs = _store(tmp_path)
    with pytest.raises(Exception):
        ws.observations("theme:nope")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /c/Users/danie/random_for_fun && .venv/Scripts/python -m pytest tests/test_wiki_observations.py -q`
Expected: FAIL with `ImportError: cannot import name 'FindingNotGated'`.

- [ ] **Step 3: Write minimal implementation**

In `gpu_agent/wiki/store.py`, extend the imports at the top:

```python
from pydantic import BaseModel
from gpu_agent.schema.finding import Finding
from gpu_agent.wiki.log import WikiLog, LogEvent, Observation, StateChange
```

(Replace the existing `from gpu_agent.wiki.log import WikiLog` line with the line above.)

Add module-level (after the existing exception classes):

```python
class FindingNotGated(ValueError):
    """Raised when append_observation references a finding absent from the FindingStore."""


class ResolvedObservation(BaseModel):
    asOf: str
    finding: Finding


class WindowView(BaseModel):
    page: WikiPage
    body: str
    observations: list[ResolvedObservation]
```

Add these methods inside `WikiStore` (after `update_header`):

```python
    def append_observation(self, page_id, finding_id, *, as_of) -> WikiPage:
        page, body = self._read(page_id)
        if not self.findings.exists(finding_id):
            raise FindingNotGated(finding_id)
        page.lastUpdatedAsOf = as_of
        self._write(page, body)
        self.log.append(asOf=as_of, kind="append-observation",
                        pageId=page_id, findingId=finding_id)
        return page

    def record_state(self, page_id, *, as_of, state, trajectory, salience, finding_id=None) -> WikiPage:
        page, body = self._read(page_id)
        page.state = state
        page.trajectory = trajectory
        page.salience = salience
        page.lastUpdatedAsOf = as_of
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
        recent = self.observations(page_id)[-n:]
        resolved = [ResolvedObservation(asOf=o.asOf, finding=self.findings.get(o.findingId))
                    for o in recent]
        return WindowView(page=page, body=body, observations=resolved)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /c/Users/danie/random_for_fun && .venv/Scripts/python -m pytest tests/test_wiki_observations.py -q`
Expected: PASS (5 passed).

- [ ] **Step 5: Run the full suite**

Run: `cd /c/Users/danie/random_for_fun && .venv/Scripts/python -m pytest -q`
Expected: 239 passed, 3 skipped.

- [ ] **Step 6: Commit**

```bash
cd /c/Users/danie/random_for_fun && git add gpu_agent/wiki/store.py tests/test_wiki_observations.py && git commit -m "feat(4-1): WikiStore observations — append_observation/record_state/window (log-derived)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 6: `WikiStore` queries — `index()` + `diff(as_of, prev_as_of)`

**Files:**
- Modify: `gpu_agent/wiki/store.py` (add `index()`, `diff()` + result types + a committed fixture-free deterministic test)
- Test: `tests/test_wiki_diff.py`

**Interfaces:**
- Consumes: the full Task 4/5 `WikiStore` (`self.log`, `self._events_for`, `get_page`, `load_page`).
- Produces (added to `WikiStore`):
  - `class IndexEntry(BaseModel)`: `id, type, title, category(Optional[str]), status, state, trajectory, salience(float), lastUpdatedAsOf, observationCount(int), oneLine(str)`
  - `class PageDelta(BaseModel)`: `id`, `title`, `newFindingIds: list[str]=[]`, `stateTransition: Optional[dict]=None`
  - `class IndexMove(BaseModel)`: `id, oldState, newState, oldTrajectory, newTrajectory, oldSalience(float), newSalience(float)`
  - `class WikiDiff(BaseModel)`: `new_pages: list[PageDelta]=[]`, `changed_pages: list[PageDelta]=[]`, `quiet_pages: list[str]=[]`, `index_moves: list[IndexMove]=[]`
  - `index(self) -> list[IndexEntry]` (scan page headers; ordered by `(category or "", id)`; cold-start → `[]`)
  - `diff(self, as_of, prev_as_of) -> WikiDiff`

- [ ] **Step 1: Write the failing test**

Create `tests/test_wiki_diff.py`:

```python
from gpu_agent.store import FindingStore
from gpu_agent.wiki.store import WikiStore
from gpu_agent.schema.finding import Finding, Kind, Impact, Confidence


def _finding(fid):
    return Finding(
        id=fid, statement="s", kind=Kind.observed, trend="flat", why="w",
        impact=Impact(targets=["x"], direction="negative", mechanism="m"),
        confidence=Confidence(level="medium", basis="b"), asOf="2026-06-26",
        indicatorId="cowosCapacity", side="supply", polarityDemand=0, polaritySupply=-1,
        magnitude=2, entity="tsmc", observedAt="2026-06-26", capturedAt="2026-06-26",
    )


def _store(tmp_path):
    fs = FindingStore(tmp_path / "findings")
    return WikiStore(tmp_path / "wiki", fs), fs


def test_index_empty_on_cold_start(tmp_path):
    ws, fs = _store(tmp_path)
    assert ws.index() == []


def test_index_orders_by_category_then_id(tmp_path):
    ws, fs = _store(tmp_path)
    ws.create_page("theme:b", "theme", "B", category="z", as_of="2026-06-26")
    ws.create_page("theme:a", "theme", "A", category="z", as_of="2026-06-26")
    ws.create_page("entity:m", "entity", "M", category="a", as_of="2026-06-26")
    assert [e.id for e in ws.index()] == ["entity:m", "theme:a", "theme:b"]


def test_index_entry_fields(tmp_path):
    ws, fs = _store(tmp_path)
    fs.append(_finding("f-1"))
    ws.create_page("theme:cowos", "theme", "CoWoS", category="chips", as_of="2026-06-26")
    ws.append_observation("theme:cowos", "f-1", as_of="2026-06-26")
    ws.record_state("theme:cowos", as_of="2026-06-26", state="slipping", trajectory="t", salience=0.7)
    e = ws.index()[0]
    assert e.observationCount == 1 and e.state == "slipping" and "slipping" in e.oneLine


def test_diff_new_changed_quiet_and_index_moves(tmp_path):
    ws, fs = _store(tmp_path)
    for i in (1, 2, 3):
        fs.append(_finding(f"f-{i}"))
    # Day 1 (2026-06-26): two pages, one observation each
    ws.create_page("theme:cowos", "theme", "CoWoS", as_of="2026-06-26")
    ws.append_observation("theme:cowos", "f-1", as_of="2026-06-26")
    ws.create_page("theme:hbm4", "theme", "HBM4", as_of="2026-06-26")
    ws.append_observation("theme:hbm4", "f-2", as_of="2026-06-26")
    # Day 2 (2026-06-27): new page; cowos gets a new obs + a state change; hbm4 stays quiet
    ws.create_page("entity:nvda", "entity", "NVDA", as_of="2026-06-27")
    ws.append_observation("theme:cowos", "f-3", as_of="2026-06-27")
    ws.record_state("theme:cowos", as_of="2026-06-27", state="slipping", trajectory="t", salience=0.7)
    d = ws.diff("2026-06-27", "2026-06-26")
    assert [p.id for p in d.new_pages] == ["entity:nvda"]
    assert [p.id for p in d.changed_pages] == ["theme:cowos"]
    assert d.quiet_pages == ["theme:hbm4"]
    assert [m.id for m in d.index_moves] == ["theme:cowos"]
    chg = d.changed_pages[0]
    assert chg.newFindingIds == ["f-3"]
    assert chg.stateTransition == {"from": "", "to": "slipping"}


def test_diff_cold_start_is_empty(tmp_path):
    ws, fs = _store(tmp_path)
    d = ws.diff("2026-06-27", "2026-06-26")
    assert d.new_pages == [] and d.changed_pages == [] and d.quiet_pages == [] and d.index_moves == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /c/Users/danie/random_for_fun && .venv/Scripts/python -m pytest tests/test_wiki_diff.py -q`
Expected: FAIL with `AttributeError: 'WikiStore' object has no attribute 'index'`.

- [ ] **Step 3: Write minimal implementation**

In `gpu_agent/wiki/store.py`, add the result types module-level (after `WindowView`):

```python
from typing import Optional


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
```

Add these methods inside `WikiStore` (after `window`):

```python
    def index(self) -> list[IndexEntry]:
        entries: list[IndexEntry] = []
        for ptype in ("entity", "theme"):
            d = self.root / ptype
            if not d.exists():
                continue
            for path in sorted(d.glob("*.md")):
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
        diff = WikiDiff()
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
                diff.new_pages.append(PageDelta(id=pid, title=title,
                                                newFindingIds=new_findings, stateTransition=trans))
                continue
            if not window:
                diff.quiet_pages.append(pid)
                continue
            prev_state = self._state_at(evs, prev_as_of) or {}
            trans = None
            if prev_state.get("state") != now_state.get("state"):
                trans = {"from": prev_state.get("state", ""), "to": now_state.get("state", "")}
            diff.changed_pages.append(PageDelta(id=pid, title=title,
                                                newFindingIds=new_findings, stateTransition=trans))
            if prev_state != now_state and now_state:
                diff.index_moves.append(IndexMove(
                    id=pid,
                    oldState=prev_state.get("state", ""), newState=now_state.get("state", ""),
                    oldTrajectory=prev_state.get("trajectory", ""), newTrajectory=now_state.get("trajectory", ""),
                    oldSalience=prev_state.get("salience", 0.0), newSalience=now_state.get("salience", 0.0)))
        diff.index_moves.sort(key=lambda m: abs(m.newSalience - m.oldSalience), reverse=True)
        return diff
```

Note: the `from typing import Optional` line goes with the other module-level imports at the top of `store.py` (move it there if a linter prefers; functionally it is fine where added).

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /c/Users/danie/random_for_fun && .venv/Scripts/python -m pytest tests/test_wiki_diff.py -q`
Expected: PASS (5 passed).

- [ ] **Step 5: Run the full suite + confirm frozen files untouched**

Run: `cd /c/Users/danie/random_for_fun && .venv/Scripts/python -m pytest -q`
Expected: 244 passed, 3 skipped.

Run: `cd /c/Users/danie/random_for_fun && git diff --stat 3a4b1a5 -- gpu_agent/gate.py gpu_agent/scoring.py gpu_agent/registry/indicators.py gpu_agent/registry/validate.py gpu_agent/schema/finding.py gpu_agent/pipeline.py`
Expected: **no output** (these frozen files are byte-unchanged since the umbrella commit).

- [ ] **Step 6: Commit**

```bash
cd /c/Users/danie/random_for_fun && git add gpu_agent/wiki/store.py tests/test_wiki_diff.py && git commit -m "feat(4-1): WikiStore queries — index() + diff(as_of, prev_as_of)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Self-Review (filled in by the plan author)

**Spec coverage:**
- FindingStore (spec §2) → Task 1. ✓
- WikiPage + no-dep frontmatter (spec §3) → Task 2. ✓
- log.jsonl / LogEvent / deterministic seq, no wall-clock (spec §4.1) → Task 3. ✓
- create_page / get_page / update_header + auto-log create-page (spec §4) → Task 4. ✓
- append_observation (refuses ungated finding) / record_state / observations / state_history / window resolving findings (spec §4, §4.2) → Task 5. ✓
- index() (deterministic order) + diff() {new/changed/quiet/index_moves} (spec §4.2, §5) → Task 6. ✓
- Cold-start graceful (spec §6) → Task 4 (`PageNotFound`), Task 6 (`test_index_empty_on_cold_start`, `test_diff_cold_start_is_empty`). ✓
- Replay / no wall-clock (spec §6) → Task 3 (`seq`), all `asOf` explicit. ✓
- Frozen byte-unchanged (spec §7) → Task 6 Step 5 `git diff --stat` guard. ✓
- Acceptance §10 items 1–6 all map to the tasks above. ✓

**Placeholder scan:** none — every step has complete code/commands.

**Type consistency:** `FindingStore`/`FindingNotFound` (T1) used in T5/T6; `WikiPage`/`dump_page`/`load_page` (T2) used in T4/T6; `WikiLog`/`LogEvent`/`Observation`/`StateChange` (T3) used in T4/T5/T6; `FindingNotGated`/`WindowView`/`ResolvedObservation` (T5) and `IndexEntry`/`PageDelta`/`IndexMove`/`WikiDiff` (T6) defined before use. `_events_for` defined in T5, used in T6 (`index`, via state reconstruction `_state_at` reads `self.log` directly). Names consistent across tasks. ✓

**Test-count math:** baseline 211 → +6 (T1) → +6 (T2) → +4 (T3) → +7 (T4) → +5 (T5) → +5 (T6) = **244 passed, 3 skipped** at the end.
