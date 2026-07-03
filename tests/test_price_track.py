"""Tests for gpu_agent/price_track.py (F49) — the Price Momentum overlay: per-series
price levels + deltas + a PMI computed from a Scorecard's price-side findings, pure and
deterministic, never blended into demandSupply/indices. Also covers the report.py
renderer (render_price_track, wired into render_report) and the brief.py overlay line.
"""
from __future__ import annotations
import json
from pathlib import Path

from gpu_agent import reader
from gpu_agent.price_track import compute_price_track, PriceTrack, PriceSeries
from gpu_agent.report import render_price_track, render_report
from gpu_agent.brief import render_state_of_market
from gpu_agent.schema.scorecard import Scorecard, DemandSupply
from gpu_agent.schema.finding import Finding, Kind, Impact, Confidence, Value, Evidence
from gpu_agent.registry.indicators import IndicatorRegistry


# ── Test helpers ─────────────────────────────────────────────────────────────

def _ev(source, url, date="2026-07-02"):
    return Evidence(source=source, url=url, date=date, excerpt="e", tier="secondary")


def _price_f(fid, *, indicatorId="D6", number, unit="USD_per_gpu_hr", entity="NVDA",
             evidence, capturedAt="2026-07-02T00:00:00Z", observedAt="2026-07-02",
             asOf="2026-07-02", magnitude=1):
    return Finding(
        id=fid, statement="s", kind=Kind.measured, trend="flat", why="w",
        impact=Impact(targets=["x"], direction="positive", mechanism="m"),
        value=Value(number=number, unit=unit),
        evidence=evidence,
        confidence=Confidence(level="medium", basis="b"), asOf=asOf,
        indicatorId=indicatorId, side="price", polarityDemand=0, polaritySupply=0,
        magnitude=magnitude, entity=entity, observedAt=observedAt, capturedAt=capturedAt)


def _sc(findings=None, as_of="2026-07-02") -> Scorecard:
    return Scorecard(
        categoryId="chips.merchant-gpu", asOf=as_of, findings=findings or [],
        demandSupply=DemandSupply(dmiContribution=0.05, smiContribution=0.02),
        narrative="n", confidence=Confidence(level="medium", basis="b"))


def _reg():
    return IndicatorRegistry.load("registry/indicators.json")


# ── compute_price_track: pin (1) live 2026-07-02 fixture ──────────────────────

def test_compute_price_track_live_fixture_3plus_series_pmi_none():
    raw = json.loads(Path("store/chips.merchant-gpu/2026-07-02-v1.json").read_text("utf-8"))
    sc = Scorecard.model_validate(raw)
    track = compute_price_track(sc, prior=None)
    assert len(track.series) >= 3
    assert track.pmi is None
    assert track.matchedSeries == 0
    # sorted by (indicatorId, publisher, unit)
    keys = [(s.indicatorId, s.publisher, s.unit) for s in track.series]
    assert keys == sorted(keys)
    # three distinct D6 publishers survive as three distinct series (F51-adjacent honesty)
    d6_publishers = {s.publisher for s in track.series if s.indicatorId == "D6"}
    assert {"lambda.ai", "coreweave.com", "runpod.io"} <= d6_publishers


# ── compute_price_track: pin (2) matching prior, 5% lower -> up, pmi 1.0 ──────

def test_compute_price_track_matching_prior_up_pmi_one():
    cur = _sc(findings=[_price_f("f-cur", number=6.69, evidence=[_ev("Lambda", "https://lambda.ai/x")])])
    prior = _sc(findings=[_price_f("f-prior", number=6.69 * 0.95,
                                   evidence=[_ev("Lambda", "https://lambda.ai/x")],
                                   capturedAt="2026-07-01T00:00:00Z", observedAt="2026-07-01",
                                   asOf="2026-07-01")], as_of="2026-07-01")
    track = compute_price_track(cur, prior)
    assert len(track.series) == 1
    s = track.series[0]
    assert s.delta > 0
    assert s.direction == "up"
    assert track.matchedSeries == 1
    assert track.pmi == 1.0


def test_compute_price_track_rel_tol_flat_case():
    cur = _sc(findings=[_price_f("f-cur", number=6.69, evidence=[_ev("Lambda", "https://lambda.ai/x")])])
    # 0.5% change — inside the 1% rel_tol -> flat, not up/down
    prior = _sc(findings=[_price_f("f-prior", number=6.69 * 0.995,
                                   evidence=[_ev("Lambda", "https://lambda.ai/x")],
                                   capturedAt="2026-07-01T00:00:00Z", observedAt="2026-07-01",
                                   asOf="2026-07-01")], as_of="2026-07-01")
    track = compute_price_track(cur, prior)
    s = track.series[0]
    assert s.direction == "flat"
    assert track.pmi == 0.0


def test_compute_price_track_no_matching_prior_delta_none():
    cur = _sc(findings=[_price_f("f-cur", number=6.69, evidence=[_ev("Lambda", "https://lambda.ai/x")])])
    prior = _sc(findings=[_price_f("f-prior", number=6.00, evidence=[_ev("CoreWeave", "https://www.coreweave.com/x")],
                                   capturedAt="2026-07-01T00:00:00Z", observedAt="2026-07-01",
                                   asOf="2026-07-01")], as_of="2026-07-01")
    track = compute_price_track(cur, prior)  # different publisher -> different series key -> no match
    s = track.series[0]
    assert s.delta is None and s.direction is None
    assert track.pmi is None
    assert track.matchedSeries == 0


# ── pin (5): compute_price_track never mutates demandSupply/indices ───────────

def test_compute_price_track_never_touches_demand_supply_or_indices():
    sc = _sc(findings=[_price_f("f-cur", number=6.69, evidence=[_ev("Lambda", "https://lambda.ai/x")])])
    before_ds = sc.demandSupply.model_copy()
    before_ix = sc.indices
    compute_price_track(sc, prior=None)
    assert sc.demandSupply == before_ds
    assert sc.indices == before_ix


# ── render_price_track (report.py) ─────────────────────────────────────────────

def test_render_price_track_omitted_when_empty():
    assert render_price_track(PriceTrack(series=[], pmi=None, matchedSeries=0)) == ""


def test_render_price_track_dead_metric_fold_when_no_deltas():
    # F67 Task 8: when every series lacks a matched-prior delta AND there's no PMI, the
    # section folds to one honest line instead of per-series "Δ vs prior: —" dash rows.
    track = PriceTrack(series=[
        PriceSeries(indicatorId="D6", unit="USD_per_gpu_hr", publisher="lambda.ai",
                   value=6.69, observedAt="2026-07-02", findingId="f-1"),
        PriceSeries(indicatorId="gpuSpotPrice", unit="USD_per_card", publisher="ebay.com",
                   value=6113.0, observedAt="2026-07-02", findingId="f-2"),
    ], pmi=None, matchedSeries=0)
    out = render_price_track(track)
    assert out == ("PRICE TRACK\n  2 price series captured; day-over-day change needs "
                   "two matched cycles")
    assert "Δ vs prior: —" not in out


def test_render_price_track_shows_pmi_when_present():
    track = PriceTrack(series=[
        PriceSeries(indicatorId="D6", unit="USD_per_gpu_hr", publisher="lambda.ai",
                   value=7.00, observedAt="2026-07-02", findingId="f-1",
                   delta=0.31, direction="up"),
    ], pmi=1.0, matchedSeries=1)
    out = render_price_track(track)
    assert "Δ vs prior: +0.31" in out
    assert "PMI: +1.00 ▲" in out


# ── render_report wiring: pin (4) position + byte-determinism ─────────────────

def test_render_report_places_price_track_in_appendix_before_entity_panel():
    # F67 Task 8: PRICE TRACK now renders in the appendix (below reader.APPENDIX_DIVIDER),
    # between the DIMENSION RATINGS / raw-index detail and ENTITY PANEL — STORYLINES
    # stays above the divider and is no longer PRICE TRACK's immediate predecessor.
    sc = _sc(findings=[_price_f("f-cur", number=6.69, evidence=[_ev("Lambda", "https://lambda.ai/x")])])
    out = render_report(sc, None, _reg(), render_ts="fixed")
    i_divider = out.index(reader.APPENDIX_DIVIDER)
    i_story = out.index("STORYLINES (tracked over time)")
    i_dims = out.index("DIMENSION RATINGS")
    i_price = out.index("PRICE TRACK")
    i_entity = out.index("ENTITY PANEL")
    assert i_story < i_divider < i_dims < i_price < i_entity


def test_render_report_omits_price_track_section_when_no_price_findings():
    sc = _sc(findings=[])
    out = render_report(sc, None, _reg(), render_ts="fixed")
    assert "PRICE TRACK" not in out


def test_render_report_byte_stable_with_price_track():
    sc = _sc(findings=[_price_f("f-cur", number=6.69, evidence=[_ev("Lambda", "https://lambda.ai/x")])])
    a = render_report(sc, None, _reg(), render_ts="fixed")
    b = render_report(sc, None, _reg(), render_ts="fixed")
    assert a == b


# ── brief.py overlay line ──────────────────────────────────────────────────────

def test_state_of_market_no_overlay_line_without_track():
    sc = _sc()
    out = render_state_of_market(sc, None)
    assert "Price overlay" not in out


def test_state_of_market_no_overlay_line_when_track_empty():
    sc = _sc()
    out = render_state_of_market(sc, None, PriceTrack(series=[], pmi=None, matchedSeries=0))
    assert "Price overlay" not in out


def test_state_of_market_never_shows_overlay_line_with_series_no_pmi():
    # F67 Task 8: the "Price overlay: … PMI …" line is dropped entirely — PMI is
    # off-allowlist above reader.APPENDIX_DIVIDER; the price story now lives only in
    # the appendix PRICE TRACK section, regardless of what track is passed in.
    sc = _sc()
    track = PriceTrack(series=[
        PriceSeries(indicatorId="D6", unit="USD_per_gpu_hr", publisher="lambda.ai",
                   value=6.69, observedAt="2026-07-02", findingId="f-1"),
        PriceSeries(indicatorId="gpuSpotPrice", unit="USD_per_card", publisher="ebay.com",
                   value=6113.0, observedAt="2026-07-02", findingId="f-2"),
    ], pmi=None, matchedSeries=0)
    out = render_state_of_market(sc, None, track)
    assert "Price overlay" not in out
    assert "PMI" not in out


def test_state_of_market_never_shows_overlay_line_with_signed_pmi():
    sc = _sc()
    track = PriceTrack(series=[
        PriceSeries(indicatorId="D6", unit="USD_per_gpu_hr", publisher="lambda.ai",
                   value=7.0, observedAt="2026-07-02", findingId="f-1", delta=0.31, direction="up"),
    ], pmi=1.0, matchedSeries=1)
    out = render_state_of_market(sc, None, track)
    assert "Price overlay" not in out
    assert "PMI" not in out
