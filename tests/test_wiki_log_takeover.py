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
