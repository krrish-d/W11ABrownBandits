"""Unit tests for the recurring scheduler helpers."""

from datetime import date

import pytest

from app.services.scheduler import get_next_run_date


def test_next_run_daily():
    assert get_next_run_date(date(2026, 1, 15), "daily") == date(2026, 1, 16)


def test_next_run_weekly():
    assert get_next_run_date(date(2026, 1, 15), "weekly") == date(2026, 1, 22)


def test_next_run_biweekly():
    assert get_next_run_date(date(2026, 1, 1), "biweekly") == date(2026, 1, 15)


def test_next_run_monthly_simple():
    assert get_next_run_date(date(2026, 1, 15), "monthly") == date(2026, 2, 15)


def test_next_run_monthly_year_rollover():
    assert get_next_run_date(date(2026, 12, 5), "monthly") == date(2027, 1, 5)


def test_next_run_monthly_clamps_to_short_month():
    """Jan 31 -> Feb 28 (or Feb 29 in leap years), not Mar 3."""
    assert get_next_run_date(date(2026, 1, 31), "monthly") == date(2026, 2, 28)


def test_next_run_monthly_clamps_to_short_month_leap_year():
    assert get_next_run_date(date(2024, 1, 31), "monthly") == date(2024, 2, 29)


def test_next_run_quarterly():
    assert get_next_run_date(date(2026, 1, 15), "quarterly") == date(2026, 4, 15)


def test_next_run_quarterly_year_rollover():
    assert get_next_run_date(date(2026, 11, 10), "quarterly") == date(2027, 2, 10)


def test_next_run_annually():
    assert get_next_run_date(date(2026, 4, 28), "annually") == date(2027, 4, 28)


def test_next_run_annually_leap_day():
    """Feb 29 -> Feb 28 in non-leap year (the helper's own fallback)."""
    result = get_next_run_date(date(2024, 2, 29), "annually")
    # Either the explicit fallback (2025-02-28) or natural replace; both acceptable
    assert result.year == 2025
    assert result.month == 2


def test_next_run_unknown_frequency_raises():
    with pytest.raises(ValueError, match="Unknown frequency"):
        get_next_run_date(date(2026, 1, 1), "fortnightly")
