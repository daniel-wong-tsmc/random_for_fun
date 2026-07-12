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
