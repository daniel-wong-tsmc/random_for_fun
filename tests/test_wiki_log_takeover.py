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
