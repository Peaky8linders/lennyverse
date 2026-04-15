"""Tests for confidence_service.

Uses a pinned reference date so recency decay is deterministic across
calendar time. The reference is 2026-04-15 (the date this test was written).
"""
from datetime import date

import pytest

from app.services.confidence_service import (
    RECENCY_HALF_LIFE,
    SUPPORT_SATURATION,
    score,
    score_tension,
    set_reference_date,
)


@pytest.fixture(autouse=True)
def _pin_now():
    set_reference_date(date(2026, 4, 15))
    yield
    set_reference_date(None)


def test_empty_sources_returns_zero():
    s = score([])
    assert s.confidence == 0.0
    assert s.support_count == 0
    assert s.newest_source == ""
    assert s.oldest_source == ""


def test_single_recent_source_has_mid_range_confidence():
    # 1 source today => support=0.2 (1/5), recency=1.0 => 0.6*0.2 + 0.4*1.0 = 0.52
    s = score(["2026-04-15"])
    assert s.support_count == 1
    assert s.newest_source == "2026-04-15"
    assert s.oldest_source == "2026-04-15"
    assert s.confidence == pytest.approx(0.52, abs=0.01)


def test_saturated_support_today_caps_at_one():
    # 5 sources today => support=1.0, recency=1.0 => 1.0
    dates = ["2026-04-15"] * 5
    s = score(dates)
    assert s.confidence == 1.0
    assert s.support_count == 5


def test_over_saturation_stays_at_one():
    dates = ["2026-04-15"] * 20
    s = score(dates)
    assert s.confidence == 1.0
    assert s.support_count == 20  # raw count preserved even though weight saturates


def test_old_single_source_decays():
    # 1 source from 4 years ago => support=0.2, recency=0.5^(4/2)=0.25
    # => 0.6*0.2 + 0.4*0.25 = 0.12 + 0.10 = 0.22
    s = score(["2022-04-15"])
    assert s.confidence == pytest.approx(0.22, abs=0.01)
    assert s.newest_source == "2022-04-15"


def test_recency_uses_newest_source_date():
    # Newest date dominates recency; oldest is reported separately
    dates = ["2020-01-01", "2026-04-15", "2023-06-01"]
    s = score(dates)
    assert s.newest_source == "2026-04-15"
    assert s.oldest_source == "2020-01-01"
    # support=3/5=0.6, recency=1.0 => 0.6*0.6 + 0.4*1.0 = 0.76
    assert s.confidence == pytest.approx(0.76, abs=0.01)


def test_invalid_dates_are_counted_as_support_but_ignored_for_recency():
    s = score(["not-a-date", "2026-04-15"])
    assert s.support_count == 2
    assert s.newest_source == "2026-04-15"


def test_recency_half_life_constant_is_respected():
    # Pinning to exactly RECENCY_HALF_LIFE years old should halve recency
    ref = date(2026, 4, 15)
    half_life_years_ago = date(ref.year - int(RECENCY_HALF_LIFE), ref.month, ref.day)
    s = score([half_life_years_ago.isoformat()])
    # 1 source => support=0.2; recency=0.5
    # => 0.6*0.2 + 0.4*0.5 = 0.12 + 0.20 = 0.32
    assert s.confidence == pytest.approx(0.32, abs=0.01)


def test_support_saturation_constant_matches_formula():
    # N == SUPPORT_SATURATION should produce full support weight
    dates = ["2026-04-15"] * SUPPORT_SATURATION
    s = score(dates)
    assert s.confidence == 1.0


def test_score_tension_marks_stronger_side_current():
    # Side A: 1 old source; side B: 4 recent sources
    a, b = score_tension(
        side_a_label="concept-a",
        side_a_dates=["2020-01-01"],
        side_b_label="concept-b",
        side_b_dates=["2026-03-01", "2026-02-01", "2025-12-01", "2025-11-01"],
    )
    assert a.current is False
    assert b.current is True
    assert b.score.confidence > a.score.confidence


def test_score_tension_tie_leaves_both_non_current():
    a, b = score_tension("a", ["2026-04-15"], "b", ["2026-04-15"])
    assert a.current is False
    assert b.current is False
    assert a.score.confidence == b.score.confidence
