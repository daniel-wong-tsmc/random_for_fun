"""Tests for gpu_agent/bands.py — the five-word band map (piece 5-2, output
surgery). Pins the boundary-inclusivity asymmetry from the spec (docs/superpowers/
specs/2026-07-02-thesis-book-design.md §4): the two positive floors are inclusive
(>=), the two negative floors are exclusive (>), so -0.05 itself is "softening"
(not "flat") and -0.30 itself is "contracting" (not "softening"). Also pins the
band_with_prior arrow formatter (rose ▲ / fell ▼ / same = / no prior ·).
"""
from __future__ import annotations

from gpu_agent.bands import BANDS, band_word, band_with_prior


# ── BANDS is the documented, retunable v1 threshold data ──────────────────────

def test_bands_is_the_exact_documented_v1_list():
    assert BANDS == [
        (0.30, "accelerating"),
        (0.05, "firm"),
        (-0.05, "flat"),
        (-0.30, "softening"),
    ]


# ── band_word: boundary inclusivity, pinned exactly ────────────────────────────

def test_band_word_accelerating_at_and_above_030():
    assert band_word(0.30) == "accelerating"
    assert band_word(0.31) == "accelerating"
    assert band_word(1.0) == "accelerating"


def test_band_word_just_below_030_is_firm():
    assert band_word(0.299999) == "firm"


def test_band_word_firm_at_and_above_005():
    assert band_word(0.05) == "firm"
    assert band_word(0.10) == "firm"


def test_band_word_just_below_005_is_flat():
    assert band_word(0.049999) == "flat"


def test_band_word_flat_spans_the_open_interval():
    assert band_word(0.0) == "flat"
    assert band_word(-0.049999) == "flat"


def test_band_word_minus_005_itself_is_softening_not_flat():
    # > -0.05 is "flat"; -0.05 fails that (not strictly greater), so it falls
    # through to the next floor: > -0.30 is "softening".
    assert band_word(-0.05) == "softening"


def test_band_word_softening_spans_the_open_interval():
    assert band_word(-0.10) == "softening"
    assert band_word(-0.299999) == "softening"


def test_band_word_minus_030_itself_is_contracting_not_softening():
    # > -0.30 is "softening"; -0.30 fails that (not strictly greater), so it
    # falls all the way through to the implicit fifth band: "contracting".
    assert band_word(-0.30) == "contracting"


def test_band_word_well_below_030_is_contracting():
    assert band_word(-0.31) == "contracting"
    assert band_word(-1.0) == "contracting"


def test_band_word_returns_lowercase():
    for v in (0.30, 0.05, 0.0, -0.05, -0.30):
        assert band_word(v) == band_word(v).lower()


# ── band_with_prior: pinned examples from the task brief ──────────────────────

def test_band_with_prior_same_band_pinned_example():
    assert band_with_prior(0.41, 0.51) == "ACCELERATING = (was ACCELERATING)"


def test_band_with_prior_fell_pinned_example():
    assert band_with_prior(0.2, 0.5) == "FIRM ▼ (was ACCELERATING)"


def test_band_with_prior_rose():
    assert band_with_prior(0.5, 0.2) == "ACCELERATING ▲ (was FIRM)"


def test_band_with_prior_fell_to_contracting():
    assert band_with_prior(-0.5, 0.1) == "CONTRACTING ▼ (was FIRM)"


def test_band_with_prior_no_prior():
    assert band_with_prior(0.41, None) == "ACCELERATING · (no prior)"


def test_band_with_prior_no_prior_from_contracting():
    assert band_with_prior(-0.9, None) == "CONTRACTING · (no prior)"


def test_band_with_prior_same_band_at_a_boundary_value():
    # Both -0.05 values band to "softening" (per the boundary rule above) ->
    # same band -> "=".
    assert band_with_prior(-0.05, -0.05) == "SOFTENING = (was SOFTENING)"
