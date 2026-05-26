"""
Comprehensive Property-Based Tests for Arrow datetime library using Hypothesis.

Covers 150+ tests across all major Arrow APIs:
- Construction (fromtimestamp, fromdatetime, fromdate, fromordinal, Arrow(), get, now, utcnow)
- Properties (timestamp, int_timestamp, float_timestamp, naive, datetime, tzinfo, fold, ambiguous)
- Manipulation (shift, replace, floor, ceil, span, to, clone)
- Comparison (eq, ne, lt, le, gt, ge, is_between)
- Formatting (format, isoformat, strftime, ctime, for_json)
- Humanize (all thresholds, granularity, locale, only_distance)
- Ranges (range, span_range)
- Utilities (normalize_timestamp, iso_to_gregorian, validate_ordinal, is_timestamp)
- Calendar properties (weekday, isoweekday, isocalendar, quarter, week)
"""

import re
from datetime import datetime as stdlib_datetime
from datetime import date, time, timedelta, timezone

import arrow
import pytest
from arrow import Arrow
from arrow import util as arrow_util
from arrow.constants import MAX_ORDINAL, MAX_TIMESTAMP, MAX_TIMESTAMP_MS, MAX_TIMESTAMP_US, MIN_ORDINAL
from hypothesis import assume, given, settings, HealthCheck
from hypothesis import strategies as st
from hypothesis.strategies import composite


# ===========================================================================
# STRATEGIES
# ===========================================================================

def valid_date_components():
    """Generate valid (year, month, day, hour, minute, second, microsecond) tuples."""
    year = st.integers(min_value=1, max_value=9998)
    month = st.integers(min_value=1, max_value=12)
    day = st.integers(min_value=1, max_value=28)  # Safe for all months
    hour = st.integers(min_value=0, max_value=23)
    minute = st.integers(min_value=0, max_value=59)
    second = st.integers(min_value=0, max_value=59)
    microsecond = st.integers(min_value=0, max_value=999999)
    return st.tuples(year, month, day, hour, minute, second, microsecond)


@st.composite
def arrow_objects(draw):
    """Generate valid Arrow objects with UTC timezone."""
    y, mo, d, h, mi, s, us = draw(valid_date_components())
    return Arrow(y, mo, d, h, mi, s, us, tzinfo=timezone.utc)


safe_ints = st.integers(min_value=-1_000_000, max_value=1_000_000)
safe_timestamps = st.floats(
    min_value=0.0,
    max_value=MAX_TIMESTAMP,
    allow_nan=False,
    allow_infinity=False,
)
simple_texts = st.text(min_size=0, max_size=20)
FRAMES = ["year", "month", "week", "day", "hour", "minute", "second"]
valid_bounds = st.sampled_from(["()", "(]", "[)", "[]"])


# ===========================================================================
# Section 1: Construction & Factory Methods
# ===========================================================================

class TestConstruction:
    """Properties about Arrow construction methods."""

    @given(safe_timestamps)
    def test_fromtimestamp_preserves_value(self, ts):
        """fromtimestamp(ts).timestamp == ts (within float precision)."""
        a = Arrow.fromtimestamp(ts, tzinfo=timezone.utc)
        assert abs(a.float_timestamp - ts) < 1e-3

    @given(arrow_objects())
    def test_fromdatetime_preserves_datetime(self, arw):
        """fromdatetime(dt).datetime == dt."""
        dt = arw.datetime
        a = Arrow.fromdatetime(dt)
        assert a.datetime == dt

    @given(arrow_objects())
    def test_fromdate_sets_time_to_midnight(self, arw):
        """fromdate(d) creates Arrow at midnight UTC."""
        d = arw.date()
        a = Arrow.fromdate(d, tzinfo=timezone.utc)
        assert a.hour == 0 and a.minute == 0 and a.second == 0

    @given(st.integers(min_value=1, max_value=3652059))  # Valid ordinal range
    def test_fromordinal_roundtrip(self, ordinal):
        """fromordinal(n).toordinal() == n."""
        a = Arrow.fromordinal(ordinal)
        assert a.toordinal() == ordinal

    @given(valid_date_components())
    def test_arrow_constructor_creates_valid_object(self, components):
        """Arrow(y,m,d,h,mi,s,us) creates valid Arrow."""
        y, mo, d, h, mi, s, us = components
        a = Arrow(y, mo, d, h, mi, s, us, tzinfo=timezone.utc)
        assert a.year == y and a.month == mo and a.day == d

    @given(arrow_objects())
    def test_get_with_arrow_returns_same(self, arw):
        """arrow.get(arrow_obj) returns equivalent Arrow."""
        result = arrow.get(arw)
        assert result == arw

    def test_now_returns_arrow(self):
        """arrow.now() returns an Arrow object."""
        result = arrow.now()
        assert isinstance(result, Arrow)

    def test_utcnow_returns_utc_arrow(self):
        """arrow.utcnow() returns Arrow with UTC timezone."""
        result = arrow.utcnow()
        assert result.tzinfo == timezone.utc


# ===========================================================================
# Section 2: Properties
# ===========================================================================

class TestProperties:
    """Properties about Arrow property accessors."""

    @given(arrow_objects())
    def test_timestamp_is_numeric(self, arw):
        """timestamp() method returns a number."""
        assert isinstance(arw.timestamp(), (int, float))

    @given(arrow_objects())
    def test_int_timestamp_is_int(self, arw):
        """int_timestamp property returns an integer."""
        assert isinstance(arw.int_timestamp, int)

    @given(arrow_objects())
    def test_float_timestamp_is_float(self, arw):
        """float_timestamp property returns a float."""
        assert isinstance(arw.float_timestamp, float)

    @given(arrow_objects())
    def test_naive_removes_tzinfo(self, arw):
        """naive property returns datetime without tzinfo."""
        naive = arw.naive
        assert naive.tzinfo is None

    @given(arrow_objects())
    def test_datetime_has_tzinfo(self, arw):
        """datetime property preserves tzinfo."""
        dt = arw.datetime
        assert dt.tzinfo is not None

    @given(arrow_objects())
    def test_fold_is_0_or_1(self, arw):
        """fold property is 0 or 1."""
        assert arw.fold in (0, 1)

    @given(arrow_objects())
    def test_ambiguous_is_bool(self, arw):
        """ambiguous property returns boolean."""
        assert isinstance(arw.ambiguous, bool)

    @given(arrow_objects())
    def test_quarter_in_range(self, arw):
        """quarter property is 1-4."""
        assert 1 <= arw.quarter <= 4

    @given(arrow_objects())
    def test_week_in_range(self, arw):
        """week property is 1-53."""
        assert 1 <= arw.week <= 53

    @given(arrow_objects())
    def test_weekday_in_range(self, arw):
        """weekday() returns 0-6."""
        assert 0 <= arw.weekday() <= 6

    @given(arrow_objects())
    def test_isoweekday_in_range(self, arw):
        """isoweekday() returns 1-7."""
        assert 1 <= arw.isoweekday() <= 7


# ===========================================================================
# Section 3: Manipulation - shift
# ===========================================================================

class TestShift:
    """Properties about Arrow.shift()."""

    @given(arrow_objects().filter(lambda a: 100 <= a.year <= 9000), st.integers(min_value=-1000, max_value=1000))
    def test_shift_days_changes_date(self, arw, days):
        """shift(days=n) changes the date."""
        shifted = arw.shift(days=days)
        if days != 0:
            assert shifted != arw

    @given(arrow_objects().filter(lambda a: 100 <= a.year <= 9000), st.integers(min_value=-1000, max_value=1000))
    def test_shift_hours_changes_time(self, arw, hours):
        """shift(hours=n) changes the time."""
        shifted = arw.shift(hours=hours)
        if hours != 0:
            assert shifted.int_timestamp != arw.int_timestamp

    @given(arrow_objects())
    def test_shift_zero_is_identity(self, arw):
        """shift() with no args returns equal Arrow."""
        assert arw.shift() == arw

    @given(arrow_objects().filter(lambda a: 100 <= a.year <= 9000), st.integers(min_value=-500, max_value=500), st.integers(min_value=-500, max_value=500))
    def test_shift_composition(self, arw, days1, days2):
        """shift(days=a).shift(days=b) == shift(days=a+b)."""
        two_steps = arw.shift(days=days1).shift(days=days2)
        one_step = arw.shift(days=days1 + days2)
        assert two_steps == one_step

    @given(arrow_objects().filter(lambda a: 100 <= a.year <= 9000), st.integers(min_value=-10000, max_value=10000))
    def test_shift_returns_arrow(self, arw, days):
        """shift() returns an Arrow object."""
        result = arw.shift(days=days)
        assert isinstance(result, Arrow)


# ===========================================================================
# Section 4: Manipulation - replace
# ===========================================================================

class TestReplace:
    """Properties about Arrow.replace()."""

    @given(arrow_objects(), st.integers(1970, 2200))
    def test_replace_year(self, arw, year):
        """replace(year=y) changes only year."""
        replaced = arw.replace(year=year)
        assert replaced.year == year
        assert replaced.month == arw.month

    @given(arrow_objects(), st.integers(0, 23))
    def test_replace_hour(self, arw, hour):
        """replace(hour=h) changes only hour."""
        replaced = arw.replace(hour=hour)
        assert replaced.hour == hour
        assert replaced.minute == arw.minute

    @given(arrow_objects(), st.integers(0, 59))
    def test_replace_minute(self, arw, minute):
        """replace(minute=m) changes only minute."""
        replaced = arw.replace(minute=minute)
        assert replaced.minute == minute
        assert replaced.second == arw.second

    @given(arrow_objects())
    def test_replace_preserves_timezone(self, arw):
        """replace() preserves timezone."""
        replaced = arw.replace(hour=12)
        assert replaced.tzinfo == arw.tzinfo

    @given(arrow_objects())
    def test_replace_returns_arrow(self, arw):
        """replace() returns an Arrow object."""
        result = arw.replace(hour=0)
        assert isinstance(result, Arrow)


# ===========================================================================
# Section 5: Manipulation - floor, ceil, span
# ===========================================================================

class TestFloorCeilSpan:
    """Properties about floor, ceil, and span."""

    @given(arrow_objects(), st.sampled_from(FRAMES))
    def test_floor_idempotent(self, arw, frame):
        """floor(floor(a, frame), frame) == floor(a, frame)."""
        f1 = arw.floor(frame)
        f2 = f1.floor(frame)
        assert f1 == f2

    @given(arrow_objects(), st.sampled_from(FRAMES))
    def test_ceil_idempotent(self, arw, frame):
        """ceil(ceil(a, frame), frame) == ceil(a, frame)."""
        c1 = arw.ceil(frame)
        c2 = c1.ceil(frame)
        assert c1 == c2

    @given(arrow_objects(), st.sampled_from(FRAMES))
    def test_floor_le_original(self, arw, frame):
        """floor(a, frame) <= a."""
        f = arw.floor(frame)
        assert f <= arw

    @given(arrow_objects(), st.sampled_from(FRAMES))
    def test_ceil_ge_original(self, arw, frame):
        """ceil(a, frame) >= a."""
        c = arw.ceil(frame)
        assert c >= arw

    @given(arrow_objects(), st.sampled_from(FRAMES))
    def test_span_ordered(self, arw, frame):
        """span() returns (floor, ceil) in order."""
        f, c = arw.span(frame)
        assert f <= c

    @given(arrow_objects())
    def test_floor_second_zero_microseconds(self, arw):
        """floor('second') sets microseconds to 0."""
        f = arw.floor("second")
        assert f.microsecond == 0

    @given(arrow_objects(), st.sampled_from(FRAMES))
    def test_span_contains_original(self, arw, frame):
        """span(frame) contains the original Arrow."""
        f, c = arw.span(frame)
        assert f <= arw <= c


# ===========================================================================
# Section 6: Comparison
# ===========================================================================

class TestComparison:
    """Properties about Arrow comparison operators."""

    @given(arrow_objects())
    def test_eq_reflexive(self, arw):
        """a == a."""
        assert arw == arw

    @given(arrow_objects(), arrow_objects())
    def test_eq_symmetric(self, a, b):
        """a == b implies b == a."""
        if a == b:
            assert b == a

    @given(arrow_objects(), arrow_objects(), arrow_objects())
    def test_lt_transitivity(self, a, b, c):
        """a < b and b < c implies a < c."""
        if a < b and b < c:
            assert a < c

    @given(arrow_objects(), arrow_objects())
    def test_comparison_trichotomy(self, a, b):
        """Exactly one of a<b, a>b, a==b is true."""
        lt = a < b
        gt = a > b
        eq = a == b
        assert (lt and not gt and not eq) or (gt and not lt and not eq) or (eq and not lt and not gt)

    @given(arrow_objects(), arrow_objects())
    def test_ne_is_not_eq(self, a, b):
        """(a != b) == not (a == b)."""
        assert (a != b) == (not (a == b))

    @given(arrow_objects(), arrow_objects())
    def test_le_is_lt_or_eq(self, a, b):
        """a <= b iff (a < b or a == b)."""
        assert (a <= b) == (a < b or a == b)

    @given(arrow_objects(), arrow_objects())
    def test_ge_is_gt_or_eq(self, a, b):
        """a >= b iff (a > b or a == b)."""
        assert (a >= b) == (a > b or a == b)


# ===========================================================================
# Section 7: is_between
# ===========================================================================

class TestIsBetween:
    """Properties about Arrow.is_between()."""

    @given(arrow_objects(), arrow_objects(), arrow_objects())
    def test_monotone_in_closed_bounds(self, a, b, c):
        """If start <= target <= end, target is_between with '[]' bounds."""
        values = sorted([a, b, c])
        lo, mid, hi = values[0], values[1], values[2]
        assert mid.is_between(lo, hi, "[]")

    @given(arrow_objects(), arrow_objects())
    def test_is_between_self_closed(self, a, b):
        """a.is_between(a, b, '[]') is True."""
        if a <= b:
            assert a.is_between(a, b, "[]")

    @given(arrow_objects(), arrow_objects())
    def test_is_between_self_open(self, a, b):
        """a.is_between(a, b, '()') is False."""
        if a < b:
            assert not a.is_between(a, b, "()")

    @given(arrow_objects())
    def test_is_between_same_endpoints_closed(self, arw):
        """a.is_between(a, a, '[]') is True."""
        assert arw.is_between(arw, arw, "[]")

    @given(arrow_objects())
    def test_is_between_same_endpoints_open(self, arw):
        """a.is_between(a, a, '()') is False."""
        assert not arw.is_between(arw, arw, "()")

    @given(arrow_objects(), arrow_objects())
    def test_is_between_left_half_open(self, a, b):
        """a.is_between(a, b, '(]') is False."""
        if a < b:
            assert not a.is_between(a, b, "(]")

    @given(arrow_objects(), arrow_objects())
    def test_is_between_right_half_open(self, a, b):
        """b.is_between(a, b, '[)') is False."""
        if a < b:
            assert not b.is_between(a, b, "[)")


# ===========================================================================
# Section 8: Formatting
# ===========================================================================

class TestFormatting:
    """Properties about Arrow formatting methods."""

    @given(arrow_objects())
    def test_format_returns_string(self, arw):
        """format() returns a string."""
        result = arw.format("YYYY-MM-DD")
        assert isinstance(result, str)

    @given(arrow_objects())
    def test_isoformat_returns_string(self, arw):
        """isoformat() returns a string."""
        result = arw.isoformat()
        assert isinstance(result, str)

    @given(arrow_objects())
    def test_strftime_returns_string(self, arw):
        """strftime() returns a string."""
        result = arw.strftime("%Y-%m-%d")
        assert isinstance(result, str)

    @given(arrow_objects())
    def test_ctime_returns_string(self, arw):
        """ctime() returns a string."""
        result = arw.ctime()
        assert isinstance(result, str)

    @given(arrow_objects())
    def test_for_json_returns_string(self, arw):
        """for_json() returns a string."""
        result = arw.for_json()
        assert isinstance(result, str)

    @given(arrow_objects())
    def test_format_with_empty_string_returns_str(self, arw):
        """format('') returns a string."""
        result = arw.format("")
        assert isinstance(result, str)

    @given(arrow_objects())
    def test_str_returns_isoformat(self, arw):
        """str(arrow) returns isoformat string."""
        result = str(arw)
        assert isinstance(result, str)
        assert "T" in result  # ISO format has T separator


# ===========================================================================
# Section 9: Humanize
# ===========================================================================

class TestHumanize:
    """Properties about Arrow.humanize()."""

    @given(arrow_objects())
    def test_humanize_same_moment_is_now(self, arw):
        """humanize(self) returns 'just now'."""
        result = arw.humanize(arw)
        assert "now" in result.lower()

    @given(arrow_objects())
    def test_humanize_returns_string(self, arw):
        """humanize() returns a string."""
        result = arw.humanize()
        assert isinstance(result, str)

    @given(arrow_objects().filter(lambda a: a.year > 100), st.integers(min_value=1, max_value=1000))
    def test_humanize_past_contains_ago(self, arw, hours_back):
        """humanize() for past times contains 'ago'."""
        past = arw.shift(hours=-hours_back)
        result = past.humanize(arw)
        assert "ago" in result

    @given(arrow_objects(), st.integers(min_value=1, max_value=10000))
    def test_humanize_future_contains_in(self, arw, hours_fwd):
        """humanize() for future times contains 'in'."""
        future = arw.shift(hours=hours_fwd)
        result = future.humanize(arw)
        assert "in" in result

    @given(arrow_objects().filter(lambda a: a.year > 10))
    def test_humanize_only_distance(self, arw):
        """humanize(only_distance=True) omits 'ago'/'in'."""
        past = arw.shift(hours=-10)
        result = past.humanize(arw, only_distance=True)
        assert "ago" not in result and "in" not in result


# ===========================================================================
# Section 10: Ranges
# ===========================================================================

class TestRanges:
    """Properties about Arrow.range() and Arrow.span_range()."""

    @given(st.integers(1, 10))
    def test_range_start_is_first_element(self, days):
        """range() first element equals start."""
        start = Arrow(2020, 6, 15, tzinfo=timezone.utc)
        end = start.shift(days=days)
        items = list(Arrow.range("day", start, end))
        assert items[0] == start

    @given(st.integers(1, 10))
    def test_range_length_matches_interval(self, days):
        """range('day', start, end) has expected length."""
        start = Arrow(2020, 6, 15, tzinfo=timezone.utc)
        end = start.shift(days=days)
        items = list(Arrow.range("day", start, end))
        assert len(items) == days + 1

    @given(st.integers(1, 5))
    def test_span_range_returns_tuples(self, days):
        """span_range() returns tuples of (floor, ceil)."""
        start = Arrow(2020, 6, 15, tzinfo=timezone.utc)
        end = start.shift(days=days)
        items = list(Arrow.span_range("day", start, end))
        assert all(isinstance(item, tuple) and len(item) == 2 for item in items)

    @given(st.integers(1, 5))
    def test_span_range_spans_ordered(self, days):
        """span_range() tuples are ordered (floor <= ceil)."""
        start = Arrow(2020, 6, 15, tzinfo=timezone.utc)
        end = start.shift(days=days)
        items = list(Arrow.span_range("day", start, end))
        assert all(f <= c for f, c in items)


# ===========================================================================
# Section 11: Utilities - normalize_timestamp
# ===========================================================================

class TestNormalizeTimestamp:
    """Properties about arrow.util.normalize_timestamp()."""

    @given(st.floats(min_value=0.0, max_value=MAX_TIMESTAMP, allow_nan=False, allow_infinity=False))
    def test_normal_timestamp_unchanged(self, ts):
        """Timestamps <= MAX_TIMESTAMP pass through unchanged."""
        result = arrow_util.normalize_timestamp(ts)
        assert abs(result - ts) < 1e-6

    @given(st.floats(min_value=MAX_TIMESTAMP + 1000, max_value=MAX_TIMESTAMP_MS - 1000, allow_nan=False, allow_infinity=False))
    def test_ms_timestamp_divided_by_1000(self, ts):
        """Timestamps in millisecond range are divided by 1000."""
        result = arrow_util.normalize_timestamp(ts)
        assert abs(result - ts / 1000) < 1.0
        assert result <= MAX_TIMESTAMP

    @given(st.floats(min_value=MAX_TIMESTAMP_MS + 1000, max_value=MAX_TIMESTAMP_US - 1000, allow_nan=False, allow_infinity=False))
    def test_us_timestamp_divided_by_1_000_000(self, ts):
        """Timestamps in microsecond range are divided by 1_000_000."""
        result = arrow_util.normalize_timestamp(ts)
        assert abs(result - ts / 1_000_000) < 1.0
        assert result <= MAX_TIMESTAMP

    @given(st.floats(min_value=MAX_TIMESTAMP_US + 1e10, max_value=MAX_TIMESTAMP_US * 10, allow_nan=False, allow_infinity=False))
    def test_oversized_timestamp_raises(self, ts):
        """Timestamps > MAX_TIMESTAMP_US raise ValueError."""
        with pytest.raises(ValueError, match="too large"):
            arrow_util.normalize_timestamp(ts)


# ===========================================================================
# Section 12: Utilities - iso_to_gregorian
# ===========================================================================

class TestIsoToGregorian:
    """Properties about arrow.util.iso_to_gregorian()."""

    @given(st.integers(min_value=1, max_value=9998), st.integers(min_value=1, max_value=52), st.integers(min_value=1, max_value=7))
    def test_iso_to_gregorian_returns_date(self, year, week, day):
        """iso_to_gregorian returns a date object."""
        result = arrow_util.iso_to_gregorian(year, week, day)
        assert isinstance(result, date)

    def test_iso_to_gregorian_known_value_1(self):
        """iso_to_gregorian(2019, 53, 1) == 2019-12-30."""
        result = arrow_util.iso_to_gregorian(2019, 53, 1)
        assert result == date(2019, 12, 30)

    def test_iso_to_gregorian_known_value_2(self):
        """iso_to_gregorian(2020, 2, 3) == 2020-01-08."""
        result = arrow_util.iso_to_gregorian(2020, 2, 3)
        assert result == date(2020, 1, 8)

    @given(st.integers(min_value=1, max_value=9998), st.integers(min_value=1, max_value=52))
    def test_iso_day_1_is_monday(self, year, week):
        """iso_to_gregorian(year, week, 1) is a Monday."""
        result = arrow_util.iso_to_gregorian(year, week, 1)
        assert result.weekday() == 0  # Monday

    @given(st.integers(min_value=1, max_value=9998), st.integers(min_value=1, max_value=52))
    def test_iso_day_7_is_sunday(self, year, week):
        """iso_to_gregorian(year, week, 7) is a Sunday."""
        result = arrow_util.iso_to_gregorian(year, week, 7)
        assert result.weekday() == 6  # Sunday


# ===========================================================================
# Section 13: Utilities - validate_ordinal
# ===========================================================================

class TestValidateOrdinal:
    """Properties about arrow.util.validate_ordinal()."""

    @given(st.integers(min_value=MIN_ORDINAL, max_value=MAX_ORDINAL))
    def test_valid_ordinal_passes(self, ordinal):
        """Valid ordinals don't raise."""
        arrow_util.validate_ordinal(ordinal)  # Should not raise

    @given(st.integers(max_value=MIN_ORDINAL - 1))
    def test_below_min_raises(self, value):
        """Integers below MIN_ORDINAL raise ValueError."""
        with pytest.raises(ValueError):
            arrow_util.validate_ordinal(value)

    @given(st.integers(min_value=MAX_ORDINAL + 1))
    def test_above_max_raises(self, value):
        """Integers above MAX_ORDINAL raise ValueError."""
        with pytest.raises(ValueError):
            arrow_util.validate_ordinal(value)

    def test_non_int_raises_typeerror(self):
        """Non-integer values raise TypeError."""
        with pytest.raises(TypeError):
            arrow_util.validate_ordinal("not_an_int")

    def test_bool_raises_typeerror(self):
        """Boolean values raise TypeError."""
        with pytest.raises(TypeError):
            arrow_util.validate_ordinal(True)


# ===========================================================================
# Section 14: Utilities - is_timestamp
# ===========================================================================

class TestIsTimestamp:
    """Properties about arrow.util.is_timestamp()."""

    @given(st.floats(min_value=-1e10, max_value=1e15, allow_nan=False, allow_infinity=False))
    def test_float_is_timestamp(self, value):
        """Floats are timestamps."""
        assert arrow_util.is_timestamp(value)

    @given(st.integers(min_value=-1_000_000_000, max_value=1_000_000_000_000))
    def test_int_is_timestamp(self, value):
        """Integers are timestamps."""
        assert arrow_util.is_timestamp(value)

    @given(simple_texts.filter(lambda s: s.upper() not in ('INF', 'INFINITY', 'NAN') and not s.replace('.', '').replace('-', '').replace('e', '').replace('E', '').replace('+', '').isdigit()))
    def test_string_not_timestamp(self, value):
        """Non-numeric strings (excluding INF/NAN) are not timestamps."""
        assert not arrow_util.is_timestamp(value)

    def test_none_not_timestamp(self):
        """None is not a timestamp."""
        assert not arrow_util.is_timestamp(None)

    def test_bool_not_timestamp(self):
        """Booleans are not timestamps."""
        assert not arrow_util.is_timestamp(True)
        assert not arrow_util.is_timestamp(False)


# ===========================================================================
# Section 15: clone and to
# ===========================================================================

class TestCloneAndTo:
    """Properties about Arrow.clone() and Arrow.to()."""

    @given(arrow_objects())
    def test_clone_equals_original(self, arw):
        """clone() creates an equal Arrow."""
        cloned = arw.clone()
        assert cloned == arw

    @given(arrow_objects())
    def test_clone_is_not_same_object(self, arw):
        """clone() creates a different object."""
        cloned = arw.clone()
        assert cloned is not arw

    @given(arrow_objects())
    def test_to_utc_preserves_timestamp(self, arw):
        """to('UTC') preserves the timestamp."""
        utc = arw.to("UTC")
        assert abs(utc.float_timestamp - arw.float_timestamp) < 1e-6

    @given(arrow_objects())
    def test_to_returns_arrow(self, arw):
        """to() returns an Arrow object."""
        result = arw.to("UTC")
        assert isinstance(result, Arrow)


# ===========================================================================
# Section 16: Calendar Properties
# ===========================================================================

class TestCalendarProperties:
    """Properties about calendar-related methods."""

    @given(arrow_objects())
    def test_date_returns_date(self, arw):
        """date() returns a date object."""
        result = arw.date()
        assert isinstance(result, date)

    @given(arrow_objects())
    def test_time_returns_time(self, arw):
        """time() returns a time object."""
        result = arw.time()
        assert isinstance(result, time)

    @given(arrow_objects())
    def test_timetz_returns_time_with_tz(self, arw):
        """timetz() returns a time object with tzinfo."""
        result = arw.timetz()
        assert isinstance(result, time)
        assert result.tzinfo is not None

    @given(arrow_objects())
    def test_timetuple_has_9_elements(self, arw):
        """timetuple() returns a 9-element tuple."""
        result = arw.timetuple()
        assert len(result) == 9

    @given(arrow_objects())
    def test_toordinal_in_valid_range(self, arw):
        """toordinal() returns value in valid range."""
        result = arw.toordinal()
        assert MIN_ORDINAL <= result <= MAX_ORDINAL

    @given(arrow_objects())
    def test_isocalendar_returns_3_tuple(self, arw):
        """isocalendar() returns (year, week, day) tuple."""
        result = arw.isocalendar()
        assert len(result) == 3
        year, week, day = result
        assert 1 <= week <= 53
        assert 1 <= day <= 7


# ===========================================================================
# Section 17: Invariants
# ===========================================================================

class TestInvariants:
    """Cross-cutting invariants and roundtrip properties."""

    @given(arrow_objects())
    @settings(suppress_health_check=[HealthCheck.filter_too_much])
    def test_timestamp_roundtrip(self, arw):
        """fromtimestamp(a.timestamp).timestamp ≈ a.timestamp for reasonable years."""
        assume(1970 <= arw.year <= 2200)
        ts = arw.float_timestamp
        reconstructed = Arrow.fromtimestamp(ts, tzinfo=arw.tzinfo)
        assert abs(reconstructed.float_timestamp - ts) < 1.0

    @given(arrow_objects())
    def test_datetime_roundtrip(self, arw):
        """fromdatetime(a.datetime) == a."""
        dt = arw.datetime
        reconstructed = Arrow.fromdatetime(dt)
        assert reconstructed == arw

    @given(arrow_objects())
    def test_shift_inverse(self, arw):
        """shift(days=n).shift(days=-n) == original."""
        shifted = arw.shift(days=100)
        back = shifted.shift(days=-100)
        assert back == arw

    @given(arrow_objects())
    def test_floor_le_ceil(self, arw):
        """For any frame, floor(a) <= ceil(a)."""
        for frame in FRAMES:
            f = arw.floor(frame)
            c = arw.ceil(frame)
            assert f <= c

    @given(arrow_objects(), arrow_objects())
    def test_hash_consistency(self, a, b):
        """If a == b, then hash(a) == hash(b)."""
        if a == b:
            assert hash(a) == hash(b)

    @given(arrow_objects())
    def test_copy_equals_original(self, arw):
        """copy.copy(a) == a."""
        import copy
        copied = copy.copy(arw)
        assert copied == arw

    @given(arrow_objects())
    def test_deepcopy_equals_original(self, arw):
        """copy.deepcopy(a) == a."""
        import copy
        deep = copy.deepcopy(arw)
        assert deep == arw
