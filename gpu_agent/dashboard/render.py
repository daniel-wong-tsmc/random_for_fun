# gpu_agent/dashboard/render.py
import html as _html

SECTION_IDS = ["headline", "trend", "top-signals", "calls",
               "demand-supply", "dimensions", "runs", "guide"]

_BADGE = {"new": "🆕 New", "official": "🏛 Official source", "impact": "💲 High impact"}
_PENDING = '<span class="pending" title="Auto-simplified from the source; a human rewrite has not been applied yet.">pending human rewrite</span>'


def esc(s):
    return _html.escape("" if s is None else str(s))


def _badges_html(badges):
    return "".join(f'<span class="badge b-{b}">{_BADGE[b]}</span>' for b in badges)


def _pending_html(pending):
    return f" {_PENDING}" if pending else ""


def _minmax(values):
    vals = [v for v in values if v is not None]
    if not vals:
        return 0.0, 1.0
    lo, hi = min(vals), max(vals)
    if lo == hi:
        lo, hi = lo - 1.0, hi + 1.0
    return lo, hi


def svg_sparkline(values, width=80, height=20):
    lo, hi = _minmax(values)
    n = max(1, len(values) - 1)
    pts = []
    for i, v in enumerate(values):
        x = (i / n) * (width - 2) + 1
        y = height - 1 - ((v - lo) / (hi - lo)) * (height - 2)
        pts.append(f"{x:.1f},{y:.1f}")
    return (f'<svg class="spark" width="{width}" height="{height}" viewBox="0 0 {width} {height}" '
            f'preserveAspectRatio="none" aria-hidden="true">'
            f'<polyline fill="none" stroke="currentColor" stroke-width="1.5" points="{" ".join(pts)}"/></svg>')


_CHART_COLORS = {"dmi": "#2563eb", "smi": "#d97706", "sdgi": "#059669"}


def svg_line_chart(series, labels, width=640, height=220):
    pad = 28
    all_vals = [v for s in series.values() for v in s]
    lo, hi = _minmax(all_vals)
    n = max(1, max((len(s) for s in series.values()), default=1) - 1)

    def x(i):
        return pad + (i / n) * (width - 2 * pad)

    def y(v):
        return height - pad - ((v - lo) / (hi - lo)) * (height - 2 * pad)

    parts = [f'<svg class="chart" width="100%" viewBox="0 0 {width} {height}" role="img">']
    zero_y = y(0.0) if lo <= 0 <= hi else None
    if zero_y is not None:
        parts.append(f'<line x1="{pad}" y1="{zero_y:.1f}" x2="{width - pad}" y2="{zero_y:.1f}" class="axis"/>')
    for key, s in series.items():
        color = _CHART_COLORS.get(key, "#64748b")
        pts = " ".join(f"{x(i):.1f},{y(v):.1f}" for i, v in enumerate(s))
        parts.append(f'<polyline fill="none" stroke="{color}" stroke-width="2" points="{pts}"/>')
        if s:
            parts.append(f'<text x="{x(len(s) - 1) + 4:.1f}" y="{y(s[-1]):.1f}" class="lbl" fill="{color}">{esc(key.upper())}</text>')
    for i, lab in enumerate(labels):
        parts.append(f'<text x="{x(i):.1f}" y="{height - 8}" class="tick" text-anchor="middle">{esc(lab)}</text>')
    parts.append("</svg>")
    return "".join(parts)


CSS = """
:root{--bg:#ffffff;--fg:#0f172a;--muted:#64748b;--card:#f8fafc;--line:#e2e8f0;--accent:#2563eb;--warn:#b45309}
@media (prefers-color-scheme:dark){:root{--bg:#0b1220;--fg:#e5e9f0;--muted:#94a3b8;--card:#111a2e;--line:#1e293b;--accent:#60a5fa;--warn:#f59e0b}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);font:16px/1.5 system-ui,-apple-system,Segoe UI,Roboto,sans-serif}
.wrap{max-width:1000px;margin:0 auto;padding:24px}
h1{font-size:26px;margin:0 0 4px}h2{font-size:19px;margin:32px 0 12px;border-bottom:1px solid var(--line);padding-bottom:6px}
.sub{color:var(--muted);font-size:14px}
.tiles{display:flex;flex-wrap:wrap;gap:12px;margin:16px 0}
.tile{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:12px 14px;min-width:170px;flex:1}
.tile .v{font-size:24px;font-weight:650}.tile .d{color:var(--muted);font-size:13px}
.card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:12px 14px;margin:10px 0}
.badge{display:inline-block;font-size:12px;padding:1px 8px;border-radius:999px;margin-right:6px;border:1px solid var(--line)}
.b-new{color:#166534}.b-official{color:#1e40af}.b-impact{color:#9a3412}
@media (prefers-color-scheme:dark){.b-new{color:#86efac}.b-official{color:#93c5fd}.b-impact{color:#fdba74}}
.pending{color:var(--warn);font-size:12px;font-style:italic}
.meta{color:var(--muted);font-size:13px}
table{border-collapse:collapse;width:100%}td,th{border-bottom:1px solid var(--line);padding:8px;text-align:left;font-size:14px}
.chart{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:8px}
.axis{stroke:var(--line)}.tick{fill:var(--muted);font-size:11px}.lbl{font-size:11px;font-weight:600}
.spark{color:var(--accent);vertical-align:middle}
.caption{color:var(--muted);font-size:13px;margin-top:6px}
details{margin-top:6px}summary{cursor:pointer;color:var(--muted);font-size:13px}
.helps{color:#166534}.hurts{color:#9a3412}
@media (prefers-color-scheme:dark){.helps{color:#86efac}.hurts{color:#fca5a5}}
"""


def _dir_word(direction):
    return {"worsening": "Worsening", "improving": "Improving"}.get(direction, "Steady")


def _sec_headline(m):
    h = m["headline"]
    tiles = "".join(
        f'<div class="tile"><div class="meta">{esc(t["label"])}</div>'
        f'<div class="v">{esc(t["value"])} {svg_sparkline(t["spark"])}</div>'
        f'<div class="d">{esc(t["delta"])} vs previous run</div></div>'
        for t in m["tiles"])
    return (f'<section id="headline"><h2>Where the market stands</h2>'
            f'<div class="card"><strong>{esc(h["rating"])} · {_dir_word(h["direction"])}</strong>'
            f'<div class="meta">Main limiting factor: {esc(h["limiting_factor"])}</div>'
            f'<p>{esc(h["state_of_market"])}{_pending_html(h["state_pending"])}</p></div>'
            f'<div class="tiles">{tiles}</div></section>')


def _sec_trend(m):
    return (f'<section id="trend"><h2>How the numbers moved</h2>'
            f'{svg_line_chart({"dmi": m["trend"]["dmi"], "smi": m["trend"]["smi"], "sdgi": m["trend"]["sdgi"]}, m["trend"]["dates"])}'
            f'<div class="caption">Up = stronger demand (DMI), tighter supply (SMI), or a wider demand-vs-supply gap (SDGI). '
            f'Read the direction, not the exact level.</div></section>')


def _impact_span(direction):
    if direction == "negative":
        return '<span class="hurts">▼ hurts the market</span>'
    if direction == "positive":
        return '<span class="helps">▲ helps the market</span>'
    return '<span class="meta">mixed</span>'


def _sec_top_signals(m):
    rows = []
    for s in m["top_signals"]:
        rows.append(
            f'<div class="card">{_badges_html(s["_badges"])}'
            f'<div>{esc(s["plain"])}{_pending_html(s["pending"])}</div>'
            f'<div class="meta">{esc(s.get("observed_at"))} · {esc(s.get("source_name"))} · {_impact_span(s.get("impact_direction"))}</div></div>')
    return (f'<section id="top-signals"><h2>Top signals — most important first</h2>'
            f'<div class="caption">Sorted most important first — newest, official-source, and highest-impact items rise to the top.</div>'
            f'{"".join(rows)}</section>')


_STATUS_LABEL = {"intact": "Still holds", "challenged": "Being questioned", "not_judged": "Too new to rate"}
_DIR_LABEL = {"strengthened": "Getting stronger", "weakened": "Getting weaker",
              "reaffirmed": "Reconfirmed", "none": ""}


def _sec_calls(m):
    cards = []
    for c in m["calls"]:
        breaks = (f'<details><summary>We\'d change our mind if …</summary>'
                  f'<div class="meta">{esc(c["breaks_if"])}</div></details>') if c.get("breaks_if") else ""
        cards.append(
            f'<div class="card"><strong>{esc(c["name"])}</strong> {_badges_html(c["_badges"])}'
            f'<div class="meta">{esc(_STATUS_LABEL.get(c["status"], c["status"]))} · '
            f'{esc(_DIR_LABEL.get(c["direction"], ""))} · Confidence: {esc(c["conviction"])} · '
            f'Tracked for {esc(c["cycles"])} runs · {esc(c["source_count"])} sources</div>'
            f'<div>{esc(c["plain"])}{_pending_html(c["pending"])}</div>{breaks}</div>')
    return (f'<section id="calls"><h2>Key claims we\'re tracking</h2>'
            f'<div class="caption">Ordered most important first.</div>{"".join(cards)}</section>')


def _sec_demand_supply(m):
    d = m["demand_supply"]
    gapword = {"demand-led": "Demand is pulling ahead", "supply-led": "Supply is pulling ahead",
               "balanced": "Roughly balanced"}.get(d.get("sdgi_direction"), "")
    return (f'<section id="demand-supply"><h2>Demand vs supply</h2>'
            f'<div class="card"><strong>{esc(gapword)}</strong>'
            f'<div class="meta">Demand momentum {d["dmi"]:+.2f} · Supply momentum {d["smi"]:+.2f} · '
            f'Gap {d["sdgi"]:+.2f}</div></div></section>')


def _sec_dimensions(m):
    rows = "".join(
        f'<tr><td>{esc(x["label"])}</td><td>{esc(x["rating"])}</td>'
        f'<td>{esc(_dir_word(x["direction"]))}</td>'
        f'<td>{esc("Backed by evidence this run" if x["evidence_status"] == "grounded" else "Little evidence this run")}</td></tr>'
        for x in m["dimensions"])
    return (f'<section id="dimensions"><h2>Where the evidence is strong (and thin)</h2>'
            f'<table><tr><th>Area</th><th>Rating</th><th>Trend</th><th>Evidence</th></tr>{rows}</table></section>')


def _sec_runs(m):
    rows = "".join(
        f'<tr><td>{esc(r["date"])}</td><td>{esc(r["findings"])} evidence points</td>'
        f'<td>{esc(r["sources"])} sources</td></tr>' for r in m["runs"])
    return (f'<section id="runs"><h2>What we\'ve done so far</h2>'
            f'<div class="caption">Each run gathers fresh evidence and re-scores the market.</div>'
            f'<table><tr><th>Run</th><th>Evidence</th><th>Sources</th></tr>{rows}</table></section>')


def _sec_guide(m):
    rows = "".join(f'<tr><td>{esc(g["term"])}</td><td>{esc(g["plain"])}</td></tr>' for g in m["glossary_rows"])
    return (f'<section id="guide"><h2>Plain-language guide</h2>'
            f'<table><tr><th>Term</th><th>Plain meaning</th></tr>{rows}</table>'
            f'<div class="caption">The index levels wobble run to run until more history builds up — read direction, not level.</div></section>')


def render_html(model):
    body = "".join(f(model) for f in (
        _sec_headline, _sec_trend, _sec_top_signals, _sec_calls,
        _sec_demand_supply, _sec_dimensions, _sec_runs, _sec_guide))
    head = (f'<h1>{esc(model["category_label"])} — Agent Dashboard</h1>'
            f'<div class="sub">Latest run {esc(model["latest_date"])} · {esc(model["run_count"])} runs · '
            f'generated {esc(model["generated_at"])}</div>')
    return (f'<!doctype html><html lang="en"><head><meta charset="utf-8">'
            f'<meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<title>{esc(model["category_label"])} — Agent Dashboard</title>'
            f'<style>{CSS}</style></head><body><div class="wrap">{head}{body}</div></body></html>')
