from __future__ import annotations


def computed_salience(store, page_id: str, *, as_of: str, contradiction: bool) -> float:
    """Deterministic salience from observable store facts (F15 — the 4-1 spec forbids
    brain-invented salience driving materiality/decay/pruning/ordering).
    Monotone in evidence mass; fresh activity, primary sourcing and a live
    contradiction each add a fixed boost."""
    obs = store.observations(page_id)
    n_total = len(obs)
    fresh = any(o.asOf == as_of for o in obs)
    primary = False
    for o in obs:
        try:
            f = store.findings.get(o.findingId)
        except Exception:
            continue
        if any(e.tier == "primary" for e in f.evidence):
            primary = True
            break
    score = (0.15 + 0.10 * min(n_total, 5) + 0.15 * (1 if fresh else 0)
             + 0.10 * (1 if primary else 0) + 0.20 * (1 if contradiction else 0))
    return min(1.0, round(score, 4))
