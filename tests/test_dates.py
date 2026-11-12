import shutil
from datetime import date, timedelta

import pytest

from zktatr.dates import parse_due

try:
    from zktatr.dates import gnu_date

    gnu_date()
    HAVE_GNU = True
except RuntimeError:
    HAVE_GNU = False

needs_gnu = pytest.mark.skipif(not HAVE_GNU, reason="GNU date not installed")


def test_iso_needs_no_date_binary():
    assert parse_due("2026-11-20") == date(2026, 11, 20)


def test_bad_iso_and_option_lookalikes_rejected():
    for bad in ("2026-13-45", "", "--help", "-1 day"):
        with pytest.raises(ValueError):
            parse_due(bad)


@needs_gnu
def test_gnu_phrases():
    today = date.today()
    assert parse_due("today") == today
    assert parse_due("tomorrow") == today + timedelta(days=1)
    assert parse_due("+3 days") == today + timedelta(days=3)
    nm = parse_due("next monday")
    assert nm.weekday() == 0 and today < nm <= today + timedelta(days=7)
    assert parse_due("next month") > today


@needs_gnu
def test_nonsense_rejected():
    with pytest.raises(ValueError):
        parse_due("whenever the moon is full")
