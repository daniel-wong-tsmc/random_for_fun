"""Per-seam SHA-256 over the canonically emitted bundle for a FIXED committed input
(fixtures/evals/hash-input.json). Any code or prompt-text change that alters emitted bytes
flips the hash; the pytest pin (tests/test_evals_baseline_pin.py) compares these against
baseline.json and turns the suite red until an eval run re-baselines."""
from __future__ import annotations
import hashlib
import json
import pathlib
from gpu_agent.evals.emit import emit_brain_bundle, load_hash_input


def compute_prompt_hashes(registry, taxonomy, hash_input_path: pathlib.Path) -> dict[str, str]:
    inputs = load_hash_input(hash_input_path)
    hashes: dict[str, str] = {}
    for seam in ("extract", "judge", "thesis"):
        bundle = emit_brain_bundle(seam, inputs[seam], registry, taxonomy)
        canonical = json.dumps(bundle, sort_keys=True, ensure_ascii=False)
        hashes[seam] = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return hashes
