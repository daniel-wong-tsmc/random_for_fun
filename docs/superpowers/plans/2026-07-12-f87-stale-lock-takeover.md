# F87 — Stale-lock takeover for the wiki log lock — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. Each code task uses superpowers:test-driven-development (test first, watch it fail, then implement).

**Goal:** When the wiki log's append lock times out, reclaim it automatically — but ONLY when its holder is provably dead on this machine and the lock is stale — so a crashed unattended run cannot brick every later run; every uncertain case still fails loud with a remedy in the message.

**Architecture:** The `O_EXCL` lock file (introduced by F25) gains a JSON identity body `{pid, hostname, timestamp}` written at acquire time. On acquire timeout, instead of raising immediately, `_acquire_lock` calls `_try_takeover`: it reads and parses the body, and reclaims the lock (unlink + one immediate retry, with a LOUD stderr line naming the dead pid and lock age) only if ALL of — body parses with the three typed fields, hostname matches this machine, age exceeds a 60s stale threshold, and the pid is provably not running (Windows: `kernel32.OpenProcess` + `GetExitCodeProcess` via `ctypes`; POSIX: `os.kill(pid, 0)`). Any failure of any condition (unparseable/legacy body, foreign host, young lock, live-or-unprovable pid) returns `None` and the caller fails loud. The locking SEMANTICS of the normal (uncontended) path are unchanged — the lock file itself now carries a body; F25's concurrency tests are byte-identical and green.

**Tech Stack:** Python 3, stdlib only (`os`, `json`, `socket`, `sys`, `ctypes`), pydantic (already present, unchanged here), pytest.

## Global Constraints

- **Change surface: `gpu_agent/wiki/log.py` (lock functions) + tests + docs. NOTHING ELSE.** No emitted-prompt changes; no `store/` edits; frozen core untouched.
- **No new dependency.** Windows pid-liveness via stdlib `ctypes` (`kernel32`) only. "Can't prove dead" always means "treat as alive" (never take over).
- **Stale threshold is 60s. Do NOT loosen it** (loosening is a QUESTION-STOP per the spec). The critical section is milliseconds; 60s is already very conservative.
- **Suite baseline on this branch (F25's): 1215 passed / 5 skipped — green at every commit.** `tests/test_evals_baseline_pin.py` stays green (no prompt touched).
- **F25's existing concurrency tests (`tests/test_wiki_log_concurrency.py`) must pass unchanged** — the normal-path locking semantics are unchanged (the test file itself stays byte-identical).
- **Merge order: this branch (`f87-stale-lock-takeover`) merges only AFTER `f25-wiki-store-scale`.** It is stacked on F25, not main.
- Tests run from the worktree root: `../../.venv/Scripts/python -m pytest -q`. Never create a venv. LF canonical. Commit messages via bash heredoc (no double quotes in `git commit -m`). `git log --oneline -1` before every commit. Trailer: `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`.

## Files

- **Modify: `gpu_agent/wiki/log.py`** — add module-level `_pid_is_dead(pid)` / `_pid_is_dead_windows(pid)`; add imports `json`, `socket`, `sys`; add `self._stale_after = 60.0` in `WikiLog.__init__`; write the identity body in `_acquire_lock`; add `_lock_identity`, `_read_lock_identity`, `_try_takeover`; restructure the `_acquire_lock` timeout branch to attempt takeover before raising; add the remedy to the `TimeoutError` message.
- **Create: `tests/test_wiki_log_takeover.py`** — pid-liveness unit tests + the 5 takeover acceptance tests.
- **Unchanged, must stay green: `tests/test_wiki_log_concurrency.py`** (acceptance #6), `tests/test_wiki_log.py`, `tests/test_wiki_log_cache.py`.
- **Docs:** this plan (risk + decision-provenance sections below) records the doc-only torn-write edge and every mechanical choice.

## Design provenance / mechanical choices (no QUESTION-STOP fired)

- **Stale threshold = 60s exactly**, as the spec leans. Not loosened (would be a QUESTION-STOP); not tightened either (no justification to). Stored as `self._stale_after = 60.0`.
- **Windows liveness = `kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION)` + `GetExitCodeProcess`** — the exact pattern named in the spec. Trustworthy and dependency-free, so the "not trustworthy → QUESTION-STOP" trigger does NOT fire. `ctypes` argtypes/restype are set so 64-bit HANDLEs are not truncated. `OpenProcess` NULL with `GetLastError()==ERROR_INVALID_PARAMETER (87)` ⇒ no such pid ⇒ provably dead; NULL with any other error (e.g. `ACCESS_DENIED 5`) ⇒ the process exists / unknown ⇒ treat as alive. A valid handle with `GetExitCodeProcess != STILL_ACTIVE (259)` ⇒ exited ⇒ dead; `== 259` ⇒ still active ⇒ alive (a process that truly exited with code 259 is conservatively read as alive — safe).
- **POSIX liveness = `os.kill(pid, 0)`**: `ProcessLookupError` ⇒ dead; `PermissionError` (exists, not ours) ⇒ alive; any other `OSError` ⇒ treat as alive. Keeps the test suite portable; Windows is the load-bearing platform.
- **Staleness measured from the body `timestamp`** (wall clock, `time.time()`), not lock-file mtime — the spec says the body carries the timestamp and takeover reads "the lock body ... lock age". (Wall clock here is fine: it governs the lock file, not the wall-clock-free event log.)
- **LOUD log line = `print("WIKI-LOCK-TAKEOVER ...", file=sys.stderr)`** — matches the repo's existing all-caps-prefix stderr convention (see `gpu_agent/cli.py` `DROPPED`, `voice-lint:`). Names the dead pid and the lock age.
- **Reclaim = unlink + exactly one immediate `O_EXCL` retry** (per spec). If that single retry loses a race (another process re-created the lock in the gap → `FileExistsError`/`PermissionError`), we return `None` and fail loud rather than loop — conservative.
- **Lock body written with `os.write(fd, ...)`** on the O_EXCL fd right after creation; the log file itself is untouched by this. Cross-process visible immediately (shared page cache); no `fsync` needed.
- **Body validation is strict**: must be a JSON object with `pid:int` (not bool), `hostname:str`, `timestamp:int|float` (not bool). Anything else (empty legacy lock, torn write, garbage) ⇒ `None` ⇒ fail loud.

## Risk notes

- **Torn-write edge (pre-existing, doc-only per spec).** Two facets, both fail safe:
  1. *Lock body:* a holder that crashes mid-`os.write` of its identity leaves a partial/garbage body. `_read_lock_identity` parses that as legacy/unparseable and returns `None` ⇒ we refuse takeover and fail loud (a human deletes the lock, exactly as before F87). No takeover on a torn body.
  2. *Event log (inherited from F25):* an append that crashes mid-line leaves a trailing partial line in `log.jsonl`. `_sync` only consumes complete newline-terminated lines (`rfind(b"\n")`), so a torn trailing line is ignored until its newline arrives; it is never mis-parsed. Not regressive; documented here for completeness.
- **Pid reuse.** If the OS reused the dead holder's pid for a new live process, liveness reports "alive" ⇒ we refuse takeover ⇒ fail loud. Safe (we never steal a lock from a live process). We only ever take over when the pid is provably dead.
- **Foreign host.** A lock written on another machine (e.g. a shared network store) is never taken over — hostname mismatch ⇒ fail loud.

## Acceptance mapping (each pinned by a test in `tests/test_wiki_log_takeover.py`, except #6)

| # | Acceptance | Mechanism | Pinning test |
|---|---|---|---|
| 1 | Dead-pid takeover; seq continuity; loud log | `_try_takeover` reclaims; `append` re-syncs then mints `seq=len(events)` | `test_takeover_dead_pid_reclaims_and_preserves_seq` |
| 2 | Live-pid refusal (test's own pid), any age | `_pid_is_dead(getpid())` is False ⇒ `None` | `test_no_takeover_when_holder_pid_is_alive` |
| 3 | Young-lock refusal | `age <= 60` ⇒ `None` | `test_no_takeover_when_lock_is_young` |
| 4 | Foreign-host refusal | `hostname != gethostname()` ⇒ `None` | `test_no_takeover_when_foreign_host` |
| 5 | Legacy/unparseable body refusal + remedy | `_read_lock_identity` returns `None`; message carries remedy | `test_no_takeover_on_legacy_or_garbage_body` |
| 6 | F25 concurrency tests unchanged & green | normal-path locking semantics unchanged | `tests/test_wiki_log_concurrency.py` (unmodified) |

## Fix round (2026-07-12 final review: FIXES NEEDED — all applied)

**Important — two-reclaimers race in `_try_takeover` (verified, reproduced, fixed).** The
reclaim unlinked the lock path unconditionally (catching only `FileNotFoundError`) based on a
body read earlier, never re-validating. If two writers timed out on the same stale lock, A could
reclaim and create a FRESH lock (live pid, fd open) before B's unlink: on Windows B's unlink
raised an UNCAUGHT `PermissionError` (WinError 32) out of `append()` — wrong contract; on POSIX
the unlink of A's open file SUCCEEDED and B double-acquired (duplicate seqs — the exact
corruption the lock prevents). Fix (commit `b6ee6e3`):

- Re-validate the body immediately before the unlink (`_read_lock_identity() != ident` ⇒ abort ⇒
  fail loud). Tuple comparison covers pid, hostname, and timestamp.
- Catch `OSError` (not just `FileNotFoundError`) on the reclaim unlink ⇒ abort ⇒ fail loud. This
  alone makes Windows fully clean (the OS refuses to delete an open lock).
- Emit the loud `WIKI-LOCK-TAKEOVER` line only AFTER the reclaim fully succeeds (a failed
  takeover no longer announces one) — mechanical choice, recorded here.
- Two new tests stage the race deterministically: `test_racing_reclaimer_aborts_when_lock_was_replaced`
  (lock swapped to a fresh live-pid body between B's checks and B's unlink — portable) and
  `test_reclaim_blocked_unlink_fails_loud_not_permissionerror` (unlink blocked by an open handle —
  Windows-only, reproduces the reviewer's crash pre-fix).
- **Residual risk (documented):** on POSIX a TOCTOU window remains between the re-read and the
  unlink — now microseconds (no probe/sleep in between) instead of seconds, in an already-rare
  double-crash scenario; Windows (the load-bearing platform) is fully safe because the OS itself
  refuses the delete and the refusal is routed to fail-loud. Atomic-rename reclaim was considered
  and rejected: renaming the shared path can capture another reclaimer's FRESH lock with no safe
  undo — strictly worse than verify-then-unlink.

**Minor 1 — orphaned empty lock on identity-write failure (fixed, commit `4c3fccb`).**
`_create_lock_file` now wraps the identity stamp: on failure it closes the fd and unlinks the
just-created lock before re-raising (an orphaned empty-body lock would be unparseable forever —
never taken over — and would brick every later append). Used at both creation sites. Pinned by
`test_failed_identity_write_does_not_orphan_lock`.

**Minor 2 — wording (fixed).** "Byte-for-byte" claims about the locking path replaced with the
accurate claim: locking SEMANTICS for non-stale paths are unchanged; the lock FILE now carries a
body; F25's concurrency tests are byte-identical and green.

Reviewer verified clean (no action): pid probe on all modes incl. ACCESS_DENIED, clock/
future-timestamp safety, identity-write partial-read window safe-by-refusal, scope, suite
reproduction.

---

## Task 1: Provable-death pid liveness probe

**Files:**
- Modify: `gpu_agent/wiki/log.py` (top-level imports; add `_pid_is_dead`, `_pid_is_dead_windows`)
- Test: `tests/test_wiki_log_takeover.py`

**Interfaces:**
- Consumes: nothing (leaf helper).
- Produces: module-level `_pid_is_dead(pid: int) -> bool` — returns `True` ONLY if `pid` is provably not running on this machine; every uncertain case returns `False` ("treat as alive"). `_pid_is_dead_windows(pid: int) -> bool` is the Windows branch.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_wiki_log_takeover.py
import json
import os
import pathlib
import socket
import subprocess
import sys
import time

import pytest

from gpu_agent.wiki.log import WikiLog, _pid_is_dead


def _dead_pid() -> int:
    """A pid whose process has exited (provably dead on this machine)."""
    proc = subprocess.Popen([sys.executable, "-c", ""])
    proc.wait()
    return proc.pid


def test_current_process_is_not_dead():
    assert _pid_is_dead(os.getpid()) is False


def test_exited_subprocess_is_dead():
    assert _pid_is_dead(_dead_pid()) is True


def test_nonpositive_pid_is_not_dead():
    assert _pid_is_dead(0) is False
    assert _pid_is_dead(-1) is False
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `../../.venv/Scripts/python -m pytest tests/test_wiki_log_takeover.py -q`
Expected: FAIL — `ImportError: cannot import name '_pid_is_dead'`.

- [ ] **Step 3: Add imports and the liveness helpers**

At the top of `gpu_agent/wiki/log.py`, extend the imports (currently `import os`, `pathlib`, `time`, `typing`, `pydantic`):

```python
from __future__ import annotations
import json
import os
import pathlib
import socket
import sys
import time
from typing import Literal, Optional
from pydantic import BaseModel
```

Add these module-level functions (place them just above `class LogEvent`):

```python
def _pid_is_dead(pid: int) -> bool:
    """True ONLY if `pid` is provably not running on this machine. Every uncertain
    case (process exists, access denied, unknown error, cannot query) returns False =
    "treat as alive", so a lock is never stolen from a possibly-live writer. Windows
    uses kernel32 OpenProcess + GetExitCodeProcess via ctypes (stdlib, no dependency);
    POSIX uses os.kill(pid, 0)."""
    if pid <= 0:
        return False
    if os.name == "nt":
        return _pid_is_dead_windows(pid)
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return True                      # no such process -> provably dead
    except PermissionError:
        return False                     # exists, not ours -> alive
    except OSError:
        return False                     # cannot tell -> treat as alive
    return False                         # signal delivered -> alive


def _pid_is_dead_windows(pid: int) -> bool:
    import ctypes
    from ctypes import wintypes

    PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
    STILL_ACTIVE = 259
    ERROR_INVALID_PARAMETER = 87

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.OpenProcess.restype = wintypes.HANDLE
    kernel32.OpenProcess.argtypes = (wintypes.DWORD, wintypes.BOOL, wintypes.DWORD)
    kernel32.GetExitCodeProcess.restype = wintypes.BOOL
    kernel32.GetExitCodeProcess.argtypes = (wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD))
    kernel32.CloseHandle.restype = wintypes.BOOL
    kernel32.CloseHandle.argtypes = (wintypes.HANDLE,)

    handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not handle:
        err = ctypes.get_last_error()
        # 87 == no process with that id exists -> provably dead. Any other error
        # (e.g. 5 ACCESS_DENIED) means the process exists or we cannot tell -> alive.
        return err == ERROR_INVALID_PARAMETER
    try:
        code = wintypes.DWORD()
        if not kernel32.GetExitCodeProcess(handle, ctypes.byref(code)):
            return False                 # could not read exit code -> treat as alive
        return code.value != STILL_ACTIVE
    finally:
        kernel32.CloseHandle(handle)
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `../../.venv/Scripts/python -m pytest tests/test_wiki_log_takeover.py -q`
Expected: PASS (3 passed).

- [ ] **Step 5: Commit**

```bash
git add gpu_agent/wiki/log.py tests/test_wiki_log_takeover.py
git commit  # heredoc message: feat(f87): provable-death pid liveness probe (stdlib/ctypes, no dep)
```

---

## Task 2: Write the lock identity body; add the remedy to the fail-loud message

**Files:**
- Modify: `gpu_agent/wiki/log.py` (`WikiLog.__init__`, `_acquire_lock`; add `_lock_identity`)
- Test: `tests/test_wiki_log_takeover.py`

**Interfaces:**
- Consumes: nothing new.
- Produces: `WikiLog._lock_identity(self) -> bytes` (JSON `{pid, hostname, timestamp}`); `_acquire_lock` now writes that body into the lock file and, on timeout, raises `TimeoutError` whose message contains the lock path AND the remedy `delete this file if no writer is running`; `WikiLog._stale_after` attribute (float seconds, default `60.0`).

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_wiki_log_takeover.py`:

```python
def test_held_lock_body_carries_identity(tmp_path):
    log = WikiLog(tmp_path / "log.jsonl")
    fd = log._acquire_lock()
    try:
        body = pathlib.Path(log._lock_path).read_text("utf-8")
        rec = json.loads(body)
        assert rec["pid"] == os.getpid()
        assert rec["hostname"] == socket.gethostname()
        assert abs(rec["timestamp"] - time.time()) < 30
    finally:
        log._release_lock(fd)


def test_timeout_message_names_path_and_remedy(tmp_path):
    log = WikiLog(tmp_path / "log.jsonl")
    log._lock_timeout = 0.1
    # A held, un-takeoverable lock (foreign host so takeover is refused) -> fail loud.
    lock = pathlib.Path(str(tmp_path / "log.jsonl") + ".lock")
    lock.parent.mkdir(parents=True, exist_ok=True)
    lock.write_text(json.dumps(
        {"pid": os.getpid(), "hostname": "some-other-host", "timestamp": time.time()}))
    with pytest.raises(TimeoutError) as ei:
        log.append(asOf="2026-07-12", kind="append-observation", pageId="p", findingId="f")
    msg = str(ei.value)
    assert log._lock_path in msg
    assert "delete this file if no writer is running" in msg
```

- [ ] **Step 2: Run the new tests to verify they fail**

Run: `../../.venv/Scripts/python -m pytest tests/test_wiki_log_takeover.py -q -k "identity or remedy"`
Expected: FAIL — the lock body is currently empty (`rec = json.loads("")` raises) and the message lacks the remedy.

- [ ] **Step 3: Add `_stale_after`, `_lock_identity`, write the body, add the remedy**

In `WikiLog.__init__`, after `self._lock_timeout = 10.0 ...`, add:

```python
        self._stale_after = 60.0         # seconds before a same-host, dead-pid lock is stale
```

Add the identity builder method (near `_acquire_lock`):

```python
    def _lock_identity(self) -> bytes:
        """The JSON identity record stamped into the lock file at acquire time, so a
        later run can decide whether a leftover lock's holder is provably dead."""
        return json.dumps({
            "pid": os.getpid(),
            "hostname": socket.gethostname(),
            "timestamp": time.time(),
        }).encode("utf-8")
```

Rewrite `_acquire_lock` to write the body on success and add the remedy to the timeout message (takeover call is added in Task 3 — for now the timeout branch just raises with the remedy):

```python
    def _acquire_lock(self) -> int:
        """Cross-process advisory lock via an O_EXCL lock file (Windows + POSIX, no deps).
        The lock body carries an identity record ({pid, hostname, timestamp}) so a later
        run can reclaim a lock whose holder is provably dead (see _try_takeover). Fails
        loud on timeout otherwise rather than silently corrupting the seq sequence."""
        deadline = time.monotonic() + self._lock_timeout
        self.path.parent.mkdir(parents=True, exist_ok=True)
        while True:
            try:
                fd = os.open(self._lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                os.write(fd, self._lock_identity())
                return fd
            except FileExistsError:
                pass                      # another writer holds it
            except PermissionError:
                pass                      # Windows: lock file is delete-pending; treat as busy
            if time.monotonic() >= deadline:
                raise TimeoutError(
                    f"wiki log lock busy: {self._lock_path} "
                    f"- delete this file if no writer is running"
                )
            time.sleep(0.005)
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `../../.venv/Scripts/python -m pytest tests/test_wiki_log_takeover.py -q`
Expected: PASS (5 passed — the 3 from Task 1 plus these 2).

- [ ] **Step 5: Confirm F25 concurrency + existing log tests still green (acceptance #6)**

Run: `../../.venv/Scripts/python -m pytest tests/test_wiki_log_concurrency.py tests/test_wiki_log.py tests/test_wiki_log_cache.py -q`
Expected: PASS (all green — writing an identity body does not change locking semantics).

- [ ] **Step 6: Commit**

```bash
git add gpu_agent/wiki/log.py tests/test_wiki_log_takeover.py
git commit  # heredoc: feat(f87): stamp {pid,hostname,timestamp} into lock; name remedy in timeout
```

---

## Task 3: Takeover on timeout when the holder is provably dead

**Files:**
- Modify: `gpu_agent/wiki/log.py` (`_acquire_lock` timeout branch; add `_read_lock_identity`, `_try_takeover`)
- Test: `tests/test_wiki_log_takeover.py`

**Interfaces:**
- Consumes: `_pid_is_dead` (Task 1), `_lock_identity` + `_stale_after` (Task 2).
- Produces: `WikiLog._read_lock_identity(self) -> Optional[tuple[int, str, float]]` — `(pid, hostname, timestamp)` or `None` if the body is missing/empty/non-JSON/mistyped. `WikiLog._try_takeover(self) -> Optional[int]` — a fresh lock fd if the lock was reclaimed, else `None`. `_acquire_lock` calls `_try_takeover` on timeout before raising.

- [ ] **Step 1: Write the failing acceptance tests**

Append to `tests/test_wiki_log_takeover.py`:

```python
def _plant_lock(tmp_path, *, pid, hostname, age_seconds):
    lock = pathlib.Path(str(tmp_path / "log.jsonl") + ".lock")
    lock.parent.mkdir(parents=True, exist_ok=True)
    lock.write_text(json.dumps(
        {"pid": pid, "hostname": hostname, "timestamp": time.time() - age_seconds}))
    return lock


def _seed(log):
    log.append(asOf="2026-07-12", kind="create-page", pageId="p")
    log.append(asOf="2026-07-12", kind="append-observation", pageId="p", findingId="f-0")


def test_takeover_dead_pid_reclaims_and_preserves_seq(tmp_path, capsys):
    log = WikiLog(tmp_path / "log.jsonl")
    log._lock_timeout = 0.1
    _seed(log)                                            # events 0 and 1 exist
    _plant_lock(tmp_path, pid=_dead_pid(), hostname=socket.gethostname(), age_seconds=120)
    ev = log.append(asOf="2026-07-12", kind="append-observation", pageId="p", findingId="f-1")
    assert ev.seq == 2                                    # continuity preserved
    seqs = [e.seq for e in WikiLog(tmp_path / "log.jsonl").read()]
    assert seqs == [0, 1, 2]
    err = capsys.readouterr().err
    assert "WIKI-LOCK-TAKEOVER" in err                   # loud log line emitted


def test_no_takeover_when_holder_pid_is_alive(tmp_path):
    log = WikiLog(tmp_path / "log.jsonl")
    log._lock_timeout = 0.1
    # Own pid = alive; old timestamp so ONLY the liveness check can refuse.
    _plant_lock(tmp_path, pid=os.getpid(), hostname=socket.gethostname(), age_seconds=120)
    with pytest.raises(TimeoutError):
        log.append(asOf="2026-07-12", kind="append-observation", pageId="p", findingId="f")


def test_no_takeover_when_lock_is_young(tmp_path):
    log = WikiLog(tmp_path / "log.jsonl")
    log._lock_timeout = 0.1
    # Dead pid but fresh (age < 60s) -> refuse.
    _plant_lock(tmp_path, pid=_dead_pid(), hostname=socket.gethostname(), age_seconds=1)
    with pytest.raises(TimeoutError):
        log.append(asOf="2026-07-12", kind="append-observation", pageId="p", findingId="f")


def test_no_takeover_when_foreign_host(tmp_path):
    log = WikiLog(tmp_path / "log.jsonl")
    log._lock_timeout = 0.1
    # Dead pid, stale, but a different machine -> refuse.
    _plant_lock(tmp_path, pid=_dead_pid(), hostname="some-other-host", age_seconds=120)
    with pytest.raises(TimeoutError):
        log.append(asOf="2026-07-12", kind="append-observation", pageId="p", findingId="f")


def test_no_takeover_on_legacy_or_garbage_body(tmp_path):
    lock = pathlib.Path(str(tmp_path / "log.jsonl") + ".lock")
    lock.parent.mkdir(parents=True, exist_ok=True)
    for body in ["", "not json {{", json.dumps({"pid": 1})]:   # empty legacy / garbage / partial
        lock.write_text(body)
        log = WikiLog(tmp_path / "log.jsonl")
        log._lock_timeout = 0.1
        with pytest.raises(TimeoutError) as ei:
            log.append(asOf="2026-07-12", kind="append-observation", pageId="p", findingId="f")
        assert "delete this file if no writer is running" in str(ei.value)
```

- [ ] **Step 2: Run the new tests to verify they fail**

Run: `../../.venv/Scripts/python -m pytest tests/test_wiki_log_takeover.py -q -k "takeover or foreign or young or legacy or alive"`
Expected: FAIL — the dead-pid test currently raises `TimeoutError` (no takeover path yet); no `WIKI-LOCK-TAKEOVER` line. (The refusal tests may already pass since the timeout still raises — that is fine; they must stay green after Step 3.)

- [ ] **Step 3: Add `_read_lock_identity` + `_try_takeover`; wire into `_acquire_lock`**

Add both methods to `WikiLog` (near `_acquire_lock`):

```python
    def _read_lock_identity(self) -> Optional[tuple[int, str, float]]:
        """Parse the lock body into (pid, hostname, timestamp), or None if it is
        missing, empty, not a JSON object, or lacks the three correctly-typed fields.
        Legacy F25 locks were empty, and a holder that crashed mid-write leaves a torn
        body; both land here -> None -> the caller refuses takeover and fails loud."""
        try:
            raw = pathlib.Path(self._lock_path).read_bytes()
        except FileNotFoundError:
            return None
        try:
            obj = json.loads(raw.decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            return None
        if not isinstance(obj, dict):
            return None
        pid = obj.get("pid")
        hostname = obj.get("hostname")
        timestamp = obj.get("timestamp")
        if not isinstance(pid, int) or isinstance(pid, bool):
            return None
        if not isinstance(hostname, str):
            return None
        if not isinstance(timestamp, (int, float)) or isinstance(timestamp, bool):
            return None
        return pid, hostname, float(timestamp)

    def _try_takeover(self) -> Optional[int]:
        """On acquire timeout, reclaim the lock ONLY if its holder is provably dead on
        THIS machine and the lock is older than the stale threshold. Any uncertainty
        (unparseable/legacy body, foreign host, young lock, live-or-unprovable pid)
        returns None so the caller fails loud. Reclaim = unlink + one immediate O_EXCL
        retry, with a LOUD stderr line naming the dead pid and the lock age."""
        ident = self._read_lock_identity()
        if ident is None:
            return None                              # legacy / unparseable / torn body
        pid, hostname, timestamp = ident
        if hostname != socket.gethostname():
            return None                              # foreign host
        age = time.time() - timestamp
        if age <= self._stale_after:
            return None                              # too young
        if not _pid_is_dead(pid):
            return None                              # live, or cannot prove dead
        print(
            f"WIKI-LOCK-TAKEOVER {self._lock_path}: reclaiming lock held by dead "
            f"pid {pid}, age {age:.0f}s",
            file=sys.stderr,
        )
        try:
            os.unlink(self._lock_path)
        except FileNotFoundError:
            pass
        try:
            fd = os.open(self._lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except (FileExistsError, PermissionError):
            return None                              # lost the one immediate retry race
        os.write(fd, self._lock_identity())
        return fd
```

In `_acquire_lock`, replace the timeout branch (the `if time.monotonic() >= deadline:` block) so it attempts takeover before raising:

```python
            if time.monotonic() >= deadline:
                fd = self._try_takeover()
                if fd is not None:
                    return fd
                raise TimeoutError(
                    f"wiki log lock busy: {self._lock_path} "
                    f"- delete this file if no writer is running"
                )
```

- [ ] **Step 4: Run the takeover tests to verify they pass**

Run: `../../.venv/Scripts/python -m pytest tests/test_wiki_log_takeover.py -q`
Expected: PASS (all takeover + liveness + body tests green).

- [ ] **Step 5: Run the full wiki-log + concurrency suite (acceptance #6)**

Run: `../../.venv/Scripts/python -m pytest tests/test_wiki_log_concurrency.py tests/test_wiki_log.py tests/test_wiki_log_cache.py tests/test_wiki_log_takeover.py -q`
Expected: PASS — concurrency tests unchanged and green; normal path unaffected.

- [ ] **Step 6: Commit**

```bash
git add gpu_agent/wiki/log.py tests/test_wiki_log_takeover.py
git commit  # heredoc: feat(f87): reclaim stale lock only when holder provably dead (loud)
```

---

## Task 4: Full-suite verification (superpowers:verification-before-completion)

**Files:** none (verification only).

- [ ] **Step 1: Run the full suite from the worktree root**

Run: `../../.venv/Scripts/python -m pytest -q`
Expected: **1215 passed + the new takeover tests, 5 skipped** — i.e. 1215 + N passed / 5 skipped, no failures. `tests/test_evals_baseline_pin.py` green.

- [ ] **Step 2: Confirm working tree is clean and no stray `.lock` under `store/`**

Run: `git status` and `git status --porcelain store/`
Expected: only intended files changed; no leftover `store/wiki/log.jsonl.lock`.

- [ ] **Step 3: Write the DONE sentinel and push**

Write `.superpowers/handoffs/f87-stale-lock-DONE.md` (ROOT path) with date, branch, commits, suite status, delivered-vs-acceptance, and the merge-order note (AFTER F25). Then `git push -u origin f87-stale-lock-takeover`. STOP before merge.

---

## Self-review (against the spec)

- **Spec "lock body gains identity record"** → Task 2 (`_lock_identity`, written in `_acquire_lock`). ✅
- **Spec takeover conditions 1–4 (parses / hostname / age>60 / provably dead)** → Task 3 `_try_takeover`, in that order; Task 1 `_pid_is_dead`. ✅
- **Spec "Windows stdlib/ctypes only, no dep, can't-prove-dead=alive"** → Task 1 `_pid_is_dead_windows`. ✅
- **Spec "everything else fail-loud + remedy in message"** → Task 2 message; Task 3 refusal returns `None`. ✅
- **Spec "loud log naming dead pid + lock age"** → Task 3 `print("WIKI-LOCK-TAKEOVER ...")`. ✅
- **Spec torn-write edge doc-only** → Risk notes above. ✅
- **Acceptance 1–6** → mapping table; #6 = unmodified `test_wiki_log_concurrency.py`. ✅
- **Change surface = log.py + tests + docs** → only those files touched. ✅
- Placeholder scan: every code step shows full code; no TBD/TODO. ✅
- Type consistency: `_pid_is_dead`, `_lock_identity`, `_read_lock_identity`, `_try_takeover`, `_stale_after` names used consistently across tasks. ✅
