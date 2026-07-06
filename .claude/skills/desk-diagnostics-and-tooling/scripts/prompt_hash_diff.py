#!/usr/bin/env python3
"""prompt_hash_diff.py -- which seam's F6 prompt hash moved, and what actually changed in
the emitted bundle?

tests/test_evals_baseline_pin.py turning red only tells you THAT a seam's emitted-prompt
bytes changed vs the committed baseline; it doesn't show you the bytes. This script (a) says
which of extract/judge/thesis drifted, and (b) can dump the full current bundle (system +
schema + user, for the fixed committed fixtures/evals/hash-input.json) to a directory so you
can diff it against a bundle you dumped BEFORE your edit -- the only reliable way to see
WHAT changed, since the hash itself is one-way.

STDLIB ONLY in this wrapper's own imports (json/argparse/subprocess/difflib/sys/pathlib).
Computing the actual bundle needs gpu_agent + pydantic, so this shells out to the repo's own
.venv python for that one step (same pattern as f74_guard.py's pytest cross-check) rather than
reimplementing prompt-building logic here, which would drift from "the same builders the live
CLI uses" (gpu_agent/evals/emit.py's own stated purpose) and could lie about what the real
hash covers.

Read-only: never writes fixtures/evals/baseline.json, never runs `eval rebaseline`.

Usage (from repo root, or pass --repo):
    # 1) which seam(s) drifted vs the committed baseline
    .venv/Scripts/python ...\\prompt_hash_diff.py status

    # 2) BEFORE an edit: snapshot the current emitted bundles
    .venv/Scripts/python ...\\prompt_hash_diff.py dump before/

    # ... make your prompt/registry/taxonomy edit ...

    # 3) AFTER the edit: snapshot again, then diff (CRLF-normalized)
    .venv/Scripts/python ...\\prompt_hash_diff.py dump after/
    .venv/Scripts/python ...\\prompt_hash_diff.py diff before/ after/

Exit codes:
    status: 0 = all three seams match baseline; 1 = at least one seam drifted
    dump:   0 = wrote all three seam bundles; 2 = operator/compute error
    diff:   0 = no textual difference in system/user between the two dumps; 1 = differences
            found (printed as a unified diff); 2 = operator error (missing dumps)
"""
from __future__ import annotations

import argparse
import difflib
import json
import subprocess
import sys
from pathlib import Path

for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

SEAMS = ("extract", "judge", "thesis")

_COMPUTE_SNIPPET = r"""
import json, sys
from gpu_agent.config import REGISTRY_PATH, TAXONOMY_PATH
from gpu_agent.evals.emit import emit_brain_bundle, load_hash_input
from gpu_agent.registry.indicators import IndicatorRegistry
from gpu_agent.registry.structure import Taxonomy

registry = IndicatorRegistry.load(REGISTRY_PATH)
taxonomy = Taxonomy.load(TAXONOMY_PATH)
inputs = load_hash_input(r"fixtures/evals/hash-input.json")
bundles = {}
for seam in ("extract", "judge", "thesis"):
    bundles[seam] = emit_brain_bundle(seam, inputs[seam], registry, taxonomy)
json.dump(bundles, sys.stdout)
"""


def find_repo_root(start: Path) -> Path | None:
    proc = subprocess.run(["git", "-C", str(start), "rev-parse", "--show-toplevel"],
                           capture_output=True, encoding="utf-8", errors="replace")
    if proc.returncode != 0:
        return None
    return Path(proc.stdout.strip())


def venv_python(repo: Path) -> Path | None:
    for p in (repo / ".venv" / "Scripts" / "python.exe", repo / ".venv" / "bin" / "python"):
        if p.exists():
            return p
    return None


def compute_current_bundles(repo: Path) -> dict:
    py = venv_python(repo)
    if py is None:
        print("error: no .venv found under repo root -- this needs gpu_agent + pydantic "
              "importable, run from a checkout with its venv set up.", file=sys.stderr)
        sys.exit(2)
    proc = subprocess.run([str(py), "-c", _COMPUTE_SNIPPET], cwd=str(repo),
                          capture_output=True, encoding="utf-8", errors="replace")
    if proc.returncode != 0:
        print(f"error computing current bundles:\n{proc.stderr}", file=sys.stderr)
        sys.exit(2)
    return json.loads(proc.stdout)


def hash_of(bundle: dict) -> str:
    import hashlib
    canonical = json.dumps(bundle, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


# ── status ────────────────────────────────────────────────────────────────────

def cmd_status(repo: Path) -> int:
    baseline_path = repo / "fixtures" / "evals" / "baseline.json"
    if not baseline_path.exists():
        print("error: no fixtures/evals/baseline.json", file=sys.stderr)
        return 2
    pinned = json.loads(baseline_path.read_text(encoding="utf-8"))["promptHashes"]
    bundles = compute_current_bundles(repo)
    drifted = []
    for seam in SEAMS:
        current_hash = hash_of(bundles[seam])
        match = current_hash == pinned[seam]
        print(f"  {seam:8s} {'MATCHES baseline' if match else 'DRIFTED'}  "
              f"(current {current_hash[:12]}... vs pinned {pinned[seam][:12]}...)")
        if not match:
            drifted.append(seam)
    if drifted:
        print()
        print(f"Drifted seam(s): {', '.join(drifted)}. This is tests/test_evals_baseline_"
              f"pin.py going red -- expected and correct if you just edited a prompt/"
              f"registry/taxonomy file. To see WHAT changed: dump a bundle from before "
              f"your edit (git stash your change, `dump before/`, restore it, `dump "
              f"after/`, then `diff before/ after/`). The unlock is the run-eval skill + "
              f"`eval rebaseline` -- never hand-edit baseline.json.")
        return 1
    print()
    print("All three seams match the committed baseline (pin is green).")
    return 0


# ── dump ──────────────────────────────────────────────────────────────────────

def cmd_dump(repo: Path, out_dir: Path) -> int:
    bundles = compute_current_bundles(repo)
    out_dir.mkdir(parents=True, exist_ok=True)
    for seam in SEAMS:
        (out_dir / f"{seam}.json").write_text(
            json.dumps(bundles[seam], indent=2, sort_keys=True, ensure_ascii=False),
            encoding="utf-8")
    print(f"wrote {out_dir}/{{{','.join(SEAMS)}}}.json")
    return 0


# ── diff ──────────────────────────────────────────────────────────────────────

def _crlf_normalize(s: str) -> list[str]:
    """CRLF-normalize before diffing: a materialized prompt file saved on Windows and one
    saved via a POSIX tool can differ ONLY in line endings, which is not a real prompt
    change (eval-driver's SKILL.md makes the same point about materialized prompt files)."""
    return s.replace("\r\n", "\n").splitlines(keepends=True)


def cmd_diff(dir_a: Path, dir_b: Path) -> int:
    any_diff = False
    for seam in SEAMS:
        pa, pb = dir_a / f"{seam}.json", dir_b / f"{seam}.json"
        if not pa.exists() or not pb.exists():
            print(f"warning: missing {seam}.json in one of the two dump dirs "
                  f"({pa.exists()=}, {pb.exists()=})", file=sys.stderr)
            continue
        ba = json.loads(pa.read_text(encoding="utf-8"))
        bb = json.loads(pb.read_text(encoding="utf-8"))
        for field in ("system", "user"):
            ta = _crlf_normalize(ba.get(field, ""))
            tb = _crlf_normalize(bb.get(field, ""))
            if ta == tb:
                continue
            any_diff = True
            print(f"=== {seam}.{field} ===")
            diff = difflib.unified_diff(ta, tb, fromfile=f"{dir_a}/{seam}.{field}",
                                        tofile=f"{dir_b}/{seam}.{field}")
            sys.stdout.writelines(diff)
            print()
        if ba.get("schema") != bb.get("schema"):
            any_diff = True
            print(f"=== {seam}.schema differs too (pydantic model_json_schema changed) ===")
    if not any_diff:
        print("No textual difference in system/user (or schema) between the two dumps.")
        return 0
    return 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                  formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--repo", default=".", help="repo root (default: cwd, auto-detected via git)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("status")
    p_dump = sub.add_parser("dump")
    p_dump.add_argument("out_dir")
    p_diff = sub.add_parser("diff")
    p_diff.add_argument("dir_a")
    p_diff.add_argument("dir_b")

    args = ap.parse_args()
    repo = find_repo_root(Path(args.repo))
    if repo is None:
        print(f"error: {args.repo} is not inside a git repo", file=sys.stderr)
        return 2

    if args.cmd == "status":
        return cmd_status(repo)
    if args.cmd == "dump":
        return cmd_dump(repo, Path(args.out_dir))
    if args.cmd == "diff":
        return cmd_diff(Path(args.dir_a), Path(args.dir_b))
    return 2


if __name__ == "__main__":
    sys.exit(main())
