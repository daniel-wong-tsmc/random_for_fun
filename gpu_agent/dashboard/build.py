import argparse
import sys
from pathlib import Path

from .glossary import load_glossary, plain_label, term_swap
from .scorecards import load_scorecards, trend_series
from .report_calls import find_latest_report, parse_calls
from .ranking import rank_findings, rank_calls
from .plain_language import (
    load_plain_language, resolve_text,
    STATE_OF_MARKET_KEY, claim_key, finding_key,
)

# F78 Task 11 — dashboard parity: the SAME change engine the text brief uses, never
# re-derived math. gpu_agent.change imports gpu_agent.report (one-way rule: report.py
# must never import change), so this import direction is allowed here.
from gpu_agent import bands
from gpu_agent import change as change_mod
from gpu_agent.config import REGISTRY_PATH
from gpu_agent.registry.indicators import IndicatorRegistry
from gpu_agent.report import load_scorecard, render_change_lines, _VERSION_RE
from gpu_agent.thesis import ThesisStore

SLOP = ["delve", "leverage", "seamless", "boasts", "robust", "in today's fast-paced",
        "tapestry", "underscore", "testament to"]
_DIM_ORDER = ["momentum", "unitEconomics", "competitiveStructure", "moat", "bottleneck", "strategicRisk"]


def _delta(cur, prev):
    if prev is None:
        return "first run"
    return f"{cur - prev:+.2f}"


def build_model(category_id, store_dir, work_dir, plain_path, generated_at):
    g = load_glossary()
    pmap = load_plain_language(plain_path)
    recs = load_scorecards(category_id, store_dir)
    if not recs:
        raise ValueError(f"no scorecards found for {category_id} under {store_dir}")
    latest = recs[-1]
    prev = recs[-2] if len(recs) > 1 else None
    ts = trend_series(recs)

    # F78 Task 11 — same engine as the text brief (parity by construction, not
    # re-derivation). `store_dir` here is the dashboard's own established convention:
    # the category's flat scorecard directory (e.g. "store/chips.merchant-gpu" — the
    # real CLI default below, and load_scorecards' own convention). The change engine /
    # ThesisStore expect the STORE ROOT (e.g. "store", holding theses/<category>/
    # alongside <category>/ — confirmed on disk). Detection honors BOTH layouts: if
    # store_dir already contains a <category_id>/ subdir it IS the root (this also
    # gracefully accepts a caller passing the store root directly); otherwise it's the
    # category dir and its parent is the root. Naive `.parent` alone was wrong for any
    # store_dir not literally named after the category (e.g. tests/dashboard/fixtures)
    # — it silently produced false first-run output (alert prior None, every horizon
    # "no run yet"); pinned by test_build_model_change_parity_sees_fixture_history.
    store_dir = Path(store_dir)
    store_root = store_dir if (store_dir / category_id).is_dir() else store_dir.parent
    cat_dir = store_dir
    latest_path = max((p for p in cat_dir.iterdir() if _VERSION_RE.match(p.name)),
                      key=lambda p: (_VERSION_RE.match(p.name).group(1),
                                     int(_VERSION_RE.match(p.name).group(2))))
    sc = load_scorecard(latest_path)
    book = None
    tstore = ThesisStore(store_root / "theses" / category_id)
    if tstore.book_path.exists():
        book = tstore.load()
    change = change_mod.build_change_report(store_root, sc, book=book)
    state = change_mod.build_state(sc, book)
    alert = change_mod.alert_state(store_root, sc, book=book)

    _reg = IndicatorRegistry.load(REGISTRY_PATH)
    change_lines = render_change_lines(change, _reg).splitlines()[1:]   # drop the header row
    what_changed = []
    for line in change_lines:
        phrase, _, rest = line.strip().partition(":")
        phrase = phrase.split(" (vs ")[0]
        what_changed.append({"phrase": phrase, "text": rest.strip()})

    counters = {"rewrites_applied": 0, "auto_simplified": 0}

    def resolve(key, original):
        text, pending = resolve_text(key, original, pmap, g)
        counters["auto_simplified" if pending else "rewrites_applied"] += 1
        return text, pending

    state_text, state_pending = resolve(STATE_OF_MARKET_KEY, latest["reason"])

    prior1 = (change.priors or {}).get("yesterday")
    tiles = []
    for label, key, cur_v, pri_v in (
            ("Demand momentum", "dmi", state.demand,
             prior1.demand if prior1 else None),
            ("Supply momentum", "smi", state.supply,
             prior1.supply if prior1 else None),
            ("Demand-vs-supply gap", "sdgi", state.sdgi,
             prior1.sdgi if prior1 else None)):
        tiles.append({"label": label,
                      "band": bands.band_with_prior(cur_v, pri_v),
                      "value": f'{latest[key]:.2f}',
                      "delta": _delta(latest[key], prev[key] if prev else None),
                      "spark": ts[key]})

    ranked_findings = rank_findings(latest["findings"], latest["as_of"], g)
    top_signals = []
    for f in ranked_findings:
        plain, pending = resolve(finding_key(f["id"]), f["statement"])
        top_signals.append({**f, "plain": plain, "pending": pending})

    report = find_latest_report(work_dir)
    calls_raw = parse_calls(Path(report).read_text(encoding="utf-8", errors="replace")) if report else []
    ranked_calls = rank_calls(calls_raw)
    calls = []
    for c in ranked_calls:
        plain, pending = resolve(claim_key(c["slug"]), c["statement"])
        calls.append({**c, "plain": plain, "pending": pending,
                      "breaks_if": term_swap(c.get("breaks_if", ""), g)})

    dims = []
    for name in _DIM_ORDER:
        d = latest["dimensions"].get(name)
        if not d:
            dims.append({"label": plain_label(name, g), "rating": "—",
                         "direction": "steady", "evidence_status": "under-supported"})
            continue
        dims.append({"label": plain_label(name, g), "rating": d["rating"] or "—",
                     "direction": d["direction"] or "steady",
                     "evidence_status": d["evidence_status"]})

    runs = [{"date": r["as_of"], "findings": r["findings_count"], "sources": r["sources_count"]} for r in recs]
    glossary_rows = [{"term": t, "plain": p} for t, p in g["prose_terms"].items()]

    model = {
        "category_label": "Merchant-GPU Market",
        "latest_date": latest["as_of"], "run_count": len(recs),
        "generated_at": generated_at,
        "headline": {"rating": latest["rating"], "direction": latest["direction"],
                     "limiting_factor": plain_label(latest["bottleneck"] or "", g) or "—",
                     "state_of_market": state_text, "state_pending": state_pending},
        "tiles": tiles, "trend": ts, "top_signals": top_signals, "calls": calls,
        "demand_supply": {"dmi": latest["dmi"], "smi": latest["smi"],
                          "sdgi": latest["sdgi"], "sdgi_direction": latest["sdgi_direction"]},
        "dimensions": dims, "runs": runs, "glossary_rows": glossary_rows,
        "slop_denylist": SLOP,
        "alert": {"color": alert.color, "prior": alert.priorColor},
        "what_changed": what_changed,
    }
    return model, {"runs": len(recs), "claims": len(calls_raw), **counters}


def build_dashboard(category_id, store_dir, work_dir, plain_path, out_path, generated_at):
    from .render import render_html
    model, summary = build_model(category_id, store_dir, work_dir, plain_path, generated_at)
    html = render_html(model)
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    Path(out_path).write_text(html, encoding="utf-8")
    summary["out"] = out_path
    return summary


def _now_stamp():
    # Single build timestamp; the only nondeterministic value, isolated here.
    from datetime import datetime
    return datetime.now().strftime("%Y-%m-%d %H:%M")


def main(argv=None):
    ap = argparse.ArgumentParser(description="Build the merchant-GPU showcase dashboard.")
    ap.add_argument("--category", default="chips.merchant-gpu")
    ap.add_argument("--store", default="store/chips.merchant-gpu")
    ap.add_argument("--work", default="work")
    ap.add_argument("--plain", default=None,
                    help="plain-language overrides json (default: store/<cat>/plain-language/<latest>.json)")
    ap.add_argument("--out", default="docs/dashboard.html")
    args = ap.parse_args(argv)

    plain = args.plain
    if plain is None:
        recs = load_scorecards(args.category, args.store)
        if recs:
            cand = Path(args.store) / "plain-language" / f'{recs[-1]["as_of"]}.json'
            plain = str(cand) if cand.exists() else None

    summary = build_dashboard(args.category, args.store, args.work, plain, args.out, _now_stamp())
    print(f'[dashboard] runs={summary["runs"]} claims={summary["claims"]} '
          f'rewrites={summary["rewrites_applied"]} auto_simplified={summary["auto_simplified"]} '
          f'-> {summary["out"]}')
    return 0


if __name__ == "__main__":
    sys.exit(main())
