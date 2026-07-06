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

    counters = {"rewrites_applied": 0, "auto_simplified": 0}

    def resolve(key, original):
        text, pending = resolve_text(key, original, pmap, g)
        counters["auto_simplified" if pending else "rewrites_applied"] += 1
        return text, pending

    state_text, state_pending = resolve(STATE_OF_MARKET_KEY, latest["reason"])

    tiles = []
    for label, key in (("Demand momentum", "dmi"), ("Supply momentum", "smi"),
                       ("Demand-vs-supply gap", "sdgi")):
        tiles.append({"label": label, "value": f'{latest[key]:.2f}',
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
