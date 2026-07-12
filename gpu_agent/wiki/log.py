from __future__ import annotations
import json
import os
import pathlib
import socket
import sys
import time
from typing import Literal, Optional
from pydantic import BaseModel


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
        self._lock_path = str(self.path) + ".lock"
        self._lock_timeout = 10.0        # seconds to wait for the append lock before failing loud
        self._stale_after = 60.0         # seconds before a same-host, dead-pid lock is stale

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

    def _lock_identity(self) -> bytes:
        """The JSON identity record stamped into the lock file at acquire time, so a
        later run can decide whether a leftover lock's holder is provably dead."""
        return json.dumps({
            "pid": os.getpid(),
            "hostname": socket.gethostname(),
            "timestamp": time.time(),
        }).encode("utf-8")

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
                fd = self._try_takeover()
                if fd is not None:
                    return fd
                raise TimeoutError(
                    f"wiki log lock busy: {self._lock_path} "
                    f"- delete this file if no writer is running"
                )
            time.sleep(0.005)

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

    def _release_lock(self, fd: int) -> None:
        os.close(fd)                      # close BEFORE unlink (Windows cannot delete an open file)
        try:
            os.unlink(self._lock_path)
        except FileNotFoundError:
            pass

    def append(self, *, asOf, kind, pageId=None, findingId=None, state=None,
               trajectory=None, salience=None, detail="") -> LogEvent:
        # F25: mint seq under an exclusive lock. Two concurrent writers can no longer both read
        # the same length and write the same seq (the TOCTOU race) - the lock serializes the
        # read-count-then-append, and _sync() first absorbs any events another writer added.
        fd = self._acquire_lock()
        try:
            self._sync()                              # deterministic, wall-clock-free
            seq = len(self._events)
            event = LogEvent(seq=seq, asOf=asOf, kind=kind, pageId=pageId,
                             findingId=findingId, state=state, trajectory=trajectory,
                             salience=salience, detail=detail)
            data = (event.model_dump_json() + "\n").encode("utf-8")
            with self.path.open("ab") as fh:
                fh.write(data)
                fh.flush()
                self._offset = fh.tell()              # advance cursor past our own line
            self._events.append(event)                # update cache in place (no reparse)
            if event.pageId:
                self._by_page.setdefault(event.pageId, []).append(event)
            return event
        finally:
            self._release_lock(fd)

    def append_event(self, event: LogEvent) -> None:
        """Append a pre-built event (brain ingest/query/lint), re-stamping seq."""
        self.append(asOf=event.asOf, kind=event.kind, pageId=event.pageId,
                    findingId=event.findingId, state=event.state,
                    trajectory=event.trajectory, salience=event.salience,
                    detail=event.detail)
