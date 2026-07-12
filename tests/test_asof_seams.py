"""F56(a): the --as-of shape is rejected loud at every CLI seam.

F52 embeds --as-of verbatim in snapshot/FindingStore doc ids, so a fat-fingered
"2026/07/03" (slashes instead of dashes) would mint a path-unsafe id downstream.
Defense-in-depth: reject non-ISO shapes at the argparse seam, naming the flag.
Driven via subprocess (the real CLI entry point) so we observe the actual argparse
exit code + stderr, not an in-process SystemExit. The extract/ingest/wiki-*/thesis/
pipeline seams were already pinned by tests/test_lane_freshness.py (db142c3); this file
adds the two remaining seams (corpus, eval).
"""
import subprocess
import sys

import pytest

PY = sys.executable
BAD = ["2026/07/03", "20260703", "2026-7-3", "", "2026-07-3"]


def _run(*args):
    return subprocess.run([PY, "-m", "gpu_agent.cli", *args], capture_output=True, text=True)


# --- corpus seam (required --as-of) ---------------------------------------

@pytest.mark.parametrize("bad", BAD)
def test_corpus_rejects_bad_as_of(bad):
    proc = _run("corpus", "--category", "chips.merchant-gpu", "--as-of", bad)
    assert proc.returncode == 2, (
        f"expected argparse to reject {bad!r} as an --as-of shape; "
        f"stdout={proc.stdout!r} stderr={proc.stderr!r}"
    )
    assert "--as-of" in proc.stderr


@pytest.mark.parametrize("good", ["2026-07", "2026-07-03"])
def test_corpus_accepts_good_as_of_shape(good):
    # A good shape passes the argparse seam; coverage mode over the store must not
    # fail at the --as-of seam (exit 2).
    proc = _run("corpus", "--category", "chips.merchant-gpu", "--store", "store", "--as-of", good)
    assert proc.returncode != 2, (
        f"good shape {good!r} hit the argparse seam: stderr={proc.stderr!r}"
    )
    assert "--as-of" not in proc.stderr


# --- eval seam (optional --as-of, "" = not-supplied sentinel) --------------

def test_eval_rejects_bad_as_of_when_supplied(tmp_path):
    # record-grade needs a run dir; a malformed --as-of must die at the argparse
    # seam first (before the handler's own "required for record-grade" check).
    proc = _run("eval", "record-grade", "--out", str(tmp_path), "--as-of", "2026/07/03")
    assert proc.returncode == 2, f"stdout={proc.stdout!r} stderr={proc.stderr!r}"
    assert "--as-of" in proc.stderr


def test_eval_empty_as_of_sentinel_preserved(tmp_path):
    # emit-brain does not require --as-of; the empty "" default must still parse
    # (argparse applies `type` to the string default, so the optional validator must
    # return "" rather than raise). It may fail later for its own reasons, but never
    # at the --as-of argparse seam.
    proc = _run("eval", "emit-brain", "--out", str(tmp_path))
    assert not (proc.returncode == 2 and "--as-of" in proc.stderr), (
        f"empty --as-of sentinel wrongly rejected at the seam: stderr={proc.stderr!r}"
    )
