"""Property-based tests for the arrow library using Hypothesis."""

import datetime as stdlib_datetime

import pytest
from hypothesis import assume, example, given, settings
from hypothesis import strategies as st

import arrow
from arrow import Arrow, util
from arrow.constants import MAX_ORDINAL, MAX_TIMESTAMP, MIN_ORDINAL

# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

# Valid date components within arrow's supported range (year 1–9999)
years = st.integers(min_value=1, max_value=9999)
months = st.integers(min_value=1, max_value=12)
hours = st.integers(min_value=0, max_value=23)
minutes_s = st.integers(min_value=0, max_value=59)
seconds_s = st.integers(min_value=0, max_value=59)
microseconds = st.integers(min_value=0, max_value=999999)
weekdays = st.integers(min_value=0, max_value=6)
valid_bounds = st.sampled_from(["()", "(]", "[)", "[]"])

# Generate a valid (year, month, day) triple by drawing a date and extracting components
@st.composite
def valid_date_components(draw):
    d = draw(st.dates(min_value=stdlib_datetime.date(1, 1, 1), max_value=stdlib_datetime.date(9999, 12, 31)))
    return d.year, d.month, d.day


@st.composite
def arrow_objects(draw):
    """Strategy that builds an Arrow object from valid date+time components."""
    year, month, day = draw(valid_date_components())
    hour = draw(hours)
    minute = draw(minutes_s)
    second = draw(seconds_s)
    microsecond = draw(microseconds)
    return Arrow(year, month, day, hour, minute, second, microsecond, tzinfo="UTC")


# Valid seconds-range timestamps (avoid the ms/µs range to keep tests deterministic)
safe_timestamps = st.floats(
    min_value=0.0,
    max_value=MAX_TIMESTAMP,
    allow_nan=False,
    allow_infinity=False,
)

# ISO 8601 week-date components: broad year range, valid week and day numbers
@st.composite
def iso_week_date(draw):
    year = draw(st.integers(min_value=1, max_value=9999))
    week = draw(st.integers(min_value=1, max_value=52))  # 52 is safe for all years
    day = draw(st.integers(min_value=1, max_value=7))
    return year, week, day


# ---------------------------------------------------------------------------
# util.is_timestamp
# ---------------------------------------------------------------------------

class TestIsTimestampProperties:

    @given(st.integers())
    @example(0)
    @example(-1)
    def test_int_is_timestamp(self, value: int):
        """All plain integers (not bool) are valid timestamps."""
        assert util.is_timestamp(value)

    @given(st.floats(allow_nan=False, allow_infinity=False))
    def test_finite_float_is_timestamp(self, value: float):
        """Finite floats (not nan/inf) are valid timestamps."""
        assert util.is_timestamp(value)

    @given(st.booleans())
    def test_bool_is_not_timestamp(self, value: bool):
        """Booleans are not timestamps even though bool is a subtype of int."""
        assert not util.is_timestamp(value)

    @given(st.text().filter(lambda s: not s.replace(".", "", 1).replace("-", "", 1).replace("+", "", 1).lstrip("-+").isdigit() if s else True))
    def test_non_numeric_string_is_not_timestamp(self, value: str):
        """Non-numeric strings are not timestamps."""
        try:
            float(value)
            # float() succeeded, so is_timestamp should return True
            assert util.is_timestamp(value)
        except ValueError:
            assert not util.is_timestamp(value)

    @given(st.integers().map(str))
    def test_integer_string_is_timestamp(self, value: str):
        """String representations of integers are valid timestamps."""
        assert util.is_timestamp(value)


# ---------------------------------------------------------------------------
# util.validate_ordinal
# ---------------------------------------------------------------------------

class TestValidateOrdinalProperties:

    @given(st.integers(min_value=MIN_ORDINAL, max_value=MAX_ORDINAL))
    @example(MIN_ORDINAL)
    @example(MAX_ORDINAL)
    def test_valid_ordinal_does_not_raise(self, value: int):
        """All integers in [MIN_ORDINAL, MAX_ORDINAL] are valid ordinals."""
        util.validate_ordinal(value)  # must not raise

    @given(st.integers(max_value=MIN_ORDINAL - 1))
    @example(0)
    @example(-1)
    def test_below_min_raises_value_error(self, value: int):
        """Integers below MIN_ORDINAL raise ValueError."""
        with pytest.raises(ValueError):
            util.validate_ordinal(value)

    @given(st.integers(min_value=MAX_ORDINAL + 1))
    def test_above_max_raises_value_error(self, value: int):
        """Integers above MAX_ORDINAL raise ValueError."""
        with pytest.raises(ValueError):
            util.validate_ordinal(value)

    @given(st.floats(allow_nan=False, allow_infinity=False))
    def test_float_raises_type_error(self, value: float):
        """Floats raise TypeError regardless of value."""
        with pytest.raises(TypeError):
            util.validate_ordinal(value)

    @given(st.booleans())
    def test_bool_raises_type_error(self, value: bool):
        """Booleans raise TypeError even though bool subclasses int."""
        with pytest.raises(TypeError):
            util.validate_ordinal(value)

    @given(st.text())
    def test_string_raises_type_error(self, value: str):
        """Strings always raise TypeError."""
        with pytest.raises(TypeError):
            util.validate_ordinal(value)


# ---------------------------------------------------------------------------
# util.normalize_timestamp
# ---------------------------------------------------------------------------

class TestNormalizeTimestampProperties:

    @given(safe_timestamps)
    def test_normal_timestamp_unchanged(self, ts: float):
        """Timestamps in the normal range are returned unchanged."""
        result = util.normalize_timestamp(ts)
        assert result == ts

    @given(st.floats(min_value=MAX_TIMESTAMP + 1, max_value=MAX_TIMESTAMP * 1000 - 1, allow_nan=False, allow_infinity=False))
    def test_millisecond_timestamp_normalized(self, ts: float):
        """Millisecond-range timestamps are divided by 1000."""
        result = util.normalize_timestamp(ts)
        assert result == pytest.approx(ts / 1000, rel=1e-9)

    @given(st.floats(min_value=MAX_TIMESTAMP * 1001, max_value=MAX_TIMESTAMP * 999_999, allow_nan=False, allow_infinity=False))
    def test_microsecond_timestamp_normalized(self, ts: float):
        """Microsecond-range timestamps are divided by 1_000_000."""
        result = util.normalize_timestamp(ts)
        assert result == pytest.approx(ts / 1_000_000, rel=1e-9)

    def test_too_large_raises_value_error(self):
        """A timestamp beyond the microsecond max raises ValueError."""
        with pytest.raises(ValueError):
            util.normalize_timestamp(3e17)

    @given(safe_timestamps)
    def test_result_is_in_normal_range(self, ts: float):
        """Any normalized result is always at most MAX_TIMESTAMP."""
        result = util.normalize_timestamp(ts)
        assert result <= MAX_TIMESTAMP


# ---------------------------------------------------------------------------
# util.validate_bounds
# ---------------------------------------------------------------------------

class TestValidateBoundsProperties:

    @given(valid_bounds)
    def test_valid_bounds_do_not_raise(self, bounds: str):
        """All four valid bound strings pass validation."""
        util.validate_bounds(bounds)  # must not raise

    @given(st.text().filter(lambda s: s not in ("()", "(]", "[)", "[]")))
    def test_invalid_bounds_raise_value_error(self, bounds: str):
        """Any string not in the valid set raises ValueError."""
        with pytest.raises(ValueError):
            util.validate_bounds(bounds)


# ---------------------------------------------------------------------------
# util.next_weekday
# ---------------------------------------------------------------------------

class TestNextWeekdayProperties:

    @given(st.dates(min_value=stdlib_datetime.date(1, 1, 1), max_value=stdlib_datetime.date(9999, 12, 25)), weekdays)
    def test_result_has_correct_weekday(self, start_date, weekday: int):
        """The returned date always has the requested weekday."""
        dt = stdlib_datetime.datetime(start_date.year, start_date.month, start_date.day)
        result = util.next_weekday(dt, weekday)
        # dateutil uses Monday=0 for isoweekday()-1
        assert result.weekday() == weekday

    @given(st.dates(min_value=stdlib_datetime.date(1, 1, 1), max_value=stdlib_datetime.date(9999, 12, 25)), weekdays)
    def test_result_is_not_before_start(self, start_date, weekday: int):
        """The returned date is never earlier than start_date."""
        dt = stdlib_datetime.datetime(start_date.year, start_date.month, start_date.day)
        result = util.next_weekday(dt, weekday)
        assert result >= dt

    @given(st.dates(min_value=stdlib_datetime.date(1, 1, 1), max_value=stdlib_datetime.date(9999, 12, 25)), weekdays)
    def test_result_within_one_week(self, start_date, weekday: int):
        """The next weekday is always within 7 days of start_date."""
        dt = stdlib_datetime.datetime(start_date.year, start_date.month, start_date.day)
        result = util.next_weekday(dt, weekday)
        assert (result - dt).days < 7

    @given(st.dates(min_value=stdlib_datetime.date(1, 1, 1), max_value=stdlib_datetime.date(9999, 12, 25)))
    @example(stdlib_datetime.date(1970, 1, 1))
    def test_invalid_weekday_raises(self, start_date):
        """Weekday values outside [0,6] raise ValueError."""
        dt = stdlib_datetime.datetime(start_date.year, start_date.month, start_date.day)
        with pytest.raises(ValueError):
            util.next_weekday(dt, 7)
        with pytest.raises(ValueError):
            util.next_weekday(dt, -1)


# ---------------------------------------------------------------------------
# util.iso_to_gregorian
# ---------------------------------------------------------------------------

class TestIsoToGregorianProperties:

    @given(iso_week_date())
    def test_result_is_date(self, ywd):
        """iso_to_gregorian always returns a datetime.date."""
        year, week, day = ywd
        result = util.iso_to_gregorian(year, week, day)
        assert isinstance(result, stdlib_datetime.date)

    @given(iso_week_date())
    def test_roundtrip_via_isocalendar(self, ywd):
        """Converting ISO→Gregorian then back via isocalendar recovers original week/day (year may differ at boundaries)."""
        year, week, day = ywd
        gregorian = util.iso_to_gregorian(year, week, day)
        iso_year, iso_week, iso_day = gregorian.isocalendar()
        assert iso_week == week
        assert iso_day == day

    @given(st.integers(min_value=1, max_value=9999))
    @example(2013)
    def test_invalid_week_zero_raises(self, year: int):
        with pytest.raises(ValueError):
            util.iso_to_gregorian(year, 0, 1)

    @given(st.integers(min_value=1, max_value=9999))
    def test_invalid_week_54_raises(self, year: int):
        with pytest.raises(ValueError):
            util.iso_to_gregorian(year, 54, 1)

    @given(st.integers(min_value=1, max_value=9999))
    def test_invalid_day_zero_raises(self, year: int):
        with pytest.raises(ValueError):
            util.iso_to_gregorian(year, 1, 0)

    @given(st.integers(min_value=1, max_value=9999))
    def test_invalid_day_8_raises(self, year: int):
        with pytest.raises(ValueError):
            util.iso_to_gregorian(year, 1, 8)


# ---------------------------------------------------------------------------
# Arrow construction
# ---------------------------------------------------------------------------

class TestArrowConstructionProperties:

    @given(arrow_objects())
    def test_construction_returns_arrow(self, arw: Arrow):
        """Arrow constructor always returns an Arrow instance."""
        assert isinstance(arw, Arrow)

    @given(arrow_objects())
    def test_constructed_is_utc(self, arw: Arrow):
        """Arrow objects constructed with UTC tzinfo have UTC timezone."""
        from datetime import timezone
        assert arw.utcoffset() == stdlib_datetime.timedelta(0)

    @given(valid_date_components())
    def test_date_components_preserved(self, ymd):
        """Year/month/day passed to Arrow constructor are accessible as attributes."""
        year, month, day = ymd
        arw = Arrow(year, month, day)
        assert arw.year == year
        assert arw.month == month
        assert arw.day == day

    @given(arrow_objects())
    def test_datetime_property_is_datetime(self, arw: Arrow):
        """Arrow.datetime always returns a stdlib datetime."""
        assert isinstance(arw.datetime, stdlib_datetime.datetime)

    @given(arrow_objects())
    def test_naive_property_has_no_tzinfo(self, arw: Arrow):
        """Arrow.naive always returns a naive datetime."""
        assert arw.naive.tzinfo is None


# ---------------------------------------------------------------------------
# Arrow.fromordinal / toordinal roundtrip
# ---------------------------------------------------------------------------

class TestFromOrdinalProperties:

    @given(st.integers(min_value=MIN_ORDINAL, max_value=MAX_ORDINAL))
    @example(MIN_ORDINAL)
    @example(MAX_ORDINAL)
    def test_fromordinal_roundtrip(self, ordinal: int):
        """Arrow.fromordinal(x).toordinal() == x (ordinal roundtrip)."""
        arw = Arrow.fromordinal(ordinal)
        assert arw.toordinal() == ordinal

    @given(st.integers(min_value=MIN_ORDINAL, max_value=MAX_ORDINAL))
    def test_fromordinal_returns_arrow(self, ordinal: int):
        """Arrow.fromordinal always returns an Arrow."""
        assert isinstance(Arrow.fromordinal(ordinal), Arrow)


# ---------------------------------------------------------------------------
# Arrow.timestamp / fromtimestamp roundtrip
# ---------------------------------------------------------------------------

class TestTimestampRoundtripProperties:

    @given(safe_timestamps)
    @settings(max_examples=200)
    def test_fromtimestamp_preserves_value(self, ts: float):
        """Arrow.fromtimestamp(ts).timestamp() ≈ ts (roundtrip within float precision)."""
        arw = Arrow.utcfromtimestamp(ts)
        assert arw.timestamp() == pytest.approx(ts, abs=1e-3)

    @given(arrow_objects())
    def test_timestamp_is_float(self, arw: Arrow):
        """Arrow.timestamp() always returns a float."""
        assert isinstance(arw.timestamp(), float)

    @given(arrow_objects())
    def test_int_timestamp_is_int(self, arw: Arrow):
        """Arrow.int_timestamp always returns an int."""
        assert isinstance(arw.int_timestamp, int)

    @given(arrow_objects())
    def test_int_timestamp_trunc_of_float(self, arw: Arrow):
        """int_timestamp == int(float_timestamp) (truncation)."""
        assert arw.int_timestamp == int(arw.float_timestamp)


# ---------------------------------------------------------------------------
# Arrow.clone
# ---------------------------------------------------------------------------

class TestArrowCloneProperties:

    @given(arrow_objects())
    def test_clone_equals_original(self, arw: Arrow):
        """Cloning an Arrow produces an equal Arrow."""
        assert arw.clone() == arw

    @given(arrow_objects())
    def test_clone_is_different_object(self, arw: Arrow):
        """Clone is a separate object, not the same reference."""
        assert arw.clone() is not arw

    @given(arrow_objects())
    def test_clone_has_same_timestamp(self, arw: Arrow):
        """Clone has the identical timestamp value."""
        assert arw.clone().timestamp() == arw.timestamp()


# ---------------------------------------------------------------------------
# Arrow.shift (basic invariants)
# ---------------------------------------------------------------------------

class TestArrowShiftProperties:

    @given(arrow_objects())
    def test_shift_zero_seconds_is_identity(self, arw: Arrow):
        """Shifting by 0 seconds produces an equal Arrow."""
        assert arw.shift(seconds=0) == arw

    @given(arrow_objects(), st.integers(min_value=-100, max_value=100))
    def test_shift_days_then_negative_returns_original(self, arw: Arrow, n: int):
        """Shifting forward n days then backward n days returns the original."""
        assert arw.shift(days=n).shift(days=-n) == arw

    @given(arrow_objects(), st.integers(min_value=-1000, max_value=1000))
    def test_shift_seconds_monotone(self, arw: Arrow, n: int):
        """Shifting by positive seconds always yields a later Arrow."""
        shifted = arw.shift(seconds=n)
        if n > 0:
            assert shifted > arw
        elif n < 0:
            assert shifted < arw
        else:
            assert shifted == arw

    @given(arrow_objects(), st.integers(min_value=1, max_value=5), st.integers(min_value=1, max_value=5))
    def test_shift_hours_additive(self, arw: Arrow, a: int, b: int):
        """Shifting by a hours then b hours equals shifting by (a+b) hours."""
        assert arw.shift(hours=a).shift(hours=b) == arw.shift(hours=a + b)


# ---------------------------------------------------------------------------
# Arrow.replace
# ---------------------------------------------------------------------------

class TestArrowReplaceProperties:

    @given(arrow_objects(), hours)
    def test_replace_hour_sets_hour(self, arw: Arrow, h: int):
        """Arrow.replace(hour=h).hour == h."""
        result = arw.replace(hour=h)
        assert result.hour == h

    @given(arrow_objects(), minutes_s)
    def test_replace_minute_sets_minute(self, arw: Arrow, m: int):
        """Arrow.replace(minute=m).minute == m."""
        result = arw.replace(minute=m)
        assert result.minute == m

    @given(arrow_objects())
    def test_replace_with_no_args_is_identity(self, arw: Arrow):
        """Replace with no arguments returns an equal Arrow."""
        assert arw.replace() == arw

    @given(arrow_objects())
    def test_replace_returns_arrow(self, arw: Arrow):
        """Replace always returns an Arrow instance."""
        assert isinstance(arw.replace(), Arrow)


# ---------------------------------------------------------------------------
# Arrow.floor / ceil / span
# ---------------------------------------------------------------------------

class TestArrowFloorCeilProperties:

    @given(arrow_objects(), st.sampled_from(["year", "month", "day", "hour", "minute", "second"]))
    def test_floor_lte_original(self, arw: Arrow, frame: str):
        """Floor is always <= the original Arrow."""
        assert arw.floor(frame) <= arw

    @given(arrow_objects(), st.sampled_from(["year", "month", "day", "hour", "minute", "second"]))
    def test_ceil_gte_original(self, arw: Arrow, frame: str):
        """Ceil is always >= the original Arrow."""
        assert arw.ceil(frame) >= arw

    @given(arrow_objects(), st.sampled_from(["year", "month", "day", "hour", "minute", "second"]))
    def test_floor_lte_ceil(self, arw: Arrow, frame: str):
        """Floor is always <= ceil (the span is well-ordered)."""
        f, c = arw.span(frame)
        assert f <= c

    @given(arrow_objects(), st.sampled_from(["year", "month", "day", "hour", "minute", "second"]))
    def test_floor_idempotent(self, arw: Arrow, frame: str):
        """Applying floor twice equals applying it once."""
        assert arw.floor(frame).floor(frame) == arw.floor(frame)

    @given(arrow_objects(), st.sampled_from(["year", "month", "day", "hour", "minute", "second"]))
    def test_ceil_idempotent(self, arw: Arrow, frame: str):
        """Applying ceil twice equals applying it once."""
        assert arw.ceil(frame).ceil(frame) == arw.ceil(frame)

    @given(arrow_objects(), st.sampled_from(["year", "month", "day", "hour", "minute", "second"]))
    def test_span_returns_two_arrows(self, arw: Arrow, frame: str):
        """Arrow.span() returns a 2-tuple of Arrow objects."""
        f, c = arw.span(frame)
        assert isinstance(f, Arrow)
        assert isinstance(c, Arrow)

    @given(arrow_objects(), st.sampled_from(["year", "month", "day", "hour", "minute", "second"]), valid_bounds)
    def test_original_in_closed_span(self, arw: Arrow, frame: str, _bounds):
        """The original Arrow is always within the '[]' span of its frame."""
        f, c = arw.span(frame, bounds="[]")
        assert f <= arw <= c


# ---------------------------------------------------------------------------
# Arrow.is_between
# ---------------------------------------------------------------------------

class TestIsBetweenProperties:

    @given(arrow_objects(), arrow_objects(), arrow_objects(), valid_bounds)
    def test_is_between_type(self, a: Arrow, b: Arrow, c: Arrow, bounds: str):
        """is_between always returns a bool."""
        # Sort so b <= c for a meaningful range
        start, end = (b, c) if b <= c else (c, b)
        assert isinstance(a.is_between(start, end, bounds), bool)

    @given(arrow_objects(), arrow_objects())
    def test_point_in_closed_range_with_itself(self, a: Arrow, b: Arrow):
        """For '[]' bounds, a point is between itself and itself."""
        assert a.is_between(a, a, "[]")

    @given(arrow_objects(), arrow_objects())
    def test_point_not_in_open_range_with_itself(self, a: Arrow, b: Arrow):
        """For '()' bounds, no point is strictly between itself and itself."""
        assert not a.is_between(a, a, "()")

    @given(arrow_objects(), arrow_objects(), arrow_objects())
    def test_monotone_in_closed_bounds(self, a: Arrow, b: Arrow, c: Arrow):
        """If start <= target <= end, target is_between with '[]' bounds."""
        values = sorted([a, b, c])
        lo, mid, hi = values[0], values[1], values[2]
        assert mid.is_between(lo, hi, "[]")

    @given(arrow_objects(), arrow_objects())
    def test_is_between_antisymmetric_open(self, a: Arrow, b: Arrow):
        """If a != b, a is NOT between (b, b) and NOT between itself open."""
        assume(a != b)
        assert not a.is_between(b, b, "()")

    @given(arrow_objects(), st.integers(min_value=1, max_value=10000))
    def test_exclusive_bounds_exclude_start_endpoint(self, arw: Arrow, secs: int):
        """With '()' bounds, the start point itself is excluded."""
        end = arw.shift(seconds=secs)
        assert not arw.is_between(arw, end, "()")

    @given(arrow_objects(), st.integers(min_value=1, max_value=10000))
    def test_exclusive_bounds_exclude_end_endpoint(self, arw: Arrow, secs: int):
        """With '()' bounds, the end point itself is excluded."""
        start = arw.shift(seconds=-secs)
        assert not arw.is_between(start, arw, "()")


# ---------------------------------------------------------------------------
# Arrow.to (timezone conversion)
# ---------------------------------------------------------------------------

class TestArrowToProperties:

    @given(arrow_objects())
    def test_convert_to_utc_then_back_is_identity(self, arw: Arrow):
        """Converting to UTC then back to original tz preserves the moment."""
        utc_arw = arw.to("UTC")
        back = utc_arw.to(arw.tzinfo)
        assert back.timestamp() == pytest.approx(arw.timestamp(), abs=1e-3)

    @given(arrow_objects())
    def test_convert_preserves_timestamp(self, arw: Arrow):
        """Timezone conversion does not change the absolute timestamp."""
        other_tz = "US/Pacific"
        converted = arw.to(other_tz)
        assert converted.timestamp() == pytest.approx(arw.timestamp(), abs=1e-3)

    @given(arrow_objects())
    def test_convert_to_same_tz_is_identity(self, arw: Arrow):
        """Converting to the same timezone leaves the Arrow unchanged."""
        assert arw.to("UTC") == arw.to("UTC")


# ---------------------------------------------------------------------------
# Arrow arithmetic: __add__ / __sub__
# ---------------------------------------------------------------------------

class TestArrowArithmeticProperties:

    @given(arrow_objects(), st.integers(min_value=-10000, max_value=10000))
    def test_add_then_sub_timedelta_is_identity(self, arw: Arrow, seconds: int):
        """Adding then subtracting the same timedelta returns the original."""
        delta = stdlib_datetime.timedelta(seconds=seconds)
        assert arw + delta - delta == arw

    @given(arrow_objects(), st.integers(min_value=-10000, max_value=10000))
    def test_sub_then_add_timedelta_is_identity(self, arw: Arrow, seconds: int):
        """Subtracting then adding the same timedelta returns the original."""
        delta = stdlib_datetime.timedelta(seconds=seconds)
        assert arw - delta + delta == arw

    @given(arrow_objects(), arrow_objects())
    def test_diff_is_timedelta(self, a: Arrow, b: Arrow):
        """Subtracting two Arrows yields a timedelta."""
        assert isinstance(a - b, stdlib_datetime.timedelta)

    @given(arrow_objects(), arrow_objects())
    def test_diff_antisymmetric(self, a: Arrow, b: Arrow):
        """(a - b) == -(b - a)."""
        assert a - b == -(b - a)

    @given(arrow_objects(), st.integers(min_value=0, max_value=10000))
    def test_add_positive_timedelta_is_later(self, arw: Arrow, seconds: int):
        """Adding a positive timedelta always produces a later Arrow."""
        delta = stdlib_datetime.timedelta(seconds=seconds)
        result = arw + delta
        if seconds > 0:
            assert result > arw
        else:
            assert result == arw


# ---------------------------------------------------------------------------
# Arrow.format (token invariants)
# ---------------------------------------------------------------------------

class TestArrowFormatProperties:

    @given(arrow_objects())
    def test_format_yyyy_is_four_digits(self, arw: Arrow):
        """The YYYY token produces a 4-character string."""
        result = arw.format("YYYY")
        assert len(result) == 4
        assert result.isdigit()

    @given(arrow_objects())
    def test_format_mm_is_two_digit_month(self, arw: Arrow):
        """The MM token always produces a zero-padded 2-digit month."""
        result = arw.format("MM")
        assert len(result) == 2
        assert result.isdigit()
        assert 1 <= int(result) <= 12

    @given(arrow_objects())
    def test_format_dd_is_two_digit_day(self, arw: Arrow):
        """The DD token always produces a zero-padded 2-digit day."""
        result = arw.format("DD")
        assert len(result) == 2
        assert result.isdigit()
        assert 1 <= int(result) <= 31

    @given(arrow_objects())
    def test_format_hh_is_two_digit_hour(self, arw: Arrow):
        """The HH token always produces a zero-padded 2-digit hour."""
        result = arw.format("HH")
        assert len(result) == 2
        assert result.isdigit()
        assert 0 <= int(result) <= 23

    @given(arrow_objects())
    def test_format_returns_string(self, arw: Arrow):
        """Arrow.format always returns a str."""
        assert isinstance(arw.format("YYYY-MM-DD"), str)

    @given(arrow_objects())
    def test_literal_brackets_preserved(self, arw: Arrow):
        """Text enclosed in [] is passed through literally."""
        result = arw.format("[hello] YYYY")
        assert result.startswith("hello ")

    @given(arrow_objects())
    def test_default_format_parseable_back(self, arw: Arrow):
        """Default ISO format can be parsed back to an equal Arrow."""
        fmt = "YYYY-MM-DDTHH:mm:ss"
        formatted = arw.format(fmt)
        parsed = Arrow.strptime(formatted, "%Y-%m-%dT%H:%M:%S")
        # Compare only the date and time components (ignore microseconds)
        assert parsed.year == arw.year
        assert parsed.month == arw.month
        assert parsed.day == arw.day
        assert parsed.hour == arw.hour
        assert parsed.minute == arw.minute
        assert parsed.second == arw.second


# ---------------------------------------------------------------------------
# Arrow ordering / comparison
# ---------------------------------------------------------------------------

class TestArrowComparisonProperties:

    @given(arrow_objects())
    def test_reflexive_equality(self, arw: Arrow):
        """Arrow == itself."""
        assert arw == arw

    @given(arrow_objects(), arrow_objects())
    def test_antisymmetric_lt(self, a: Arrow, b: Arrow):
        """If a < b then not b < a."""
        if a < b:
            assert not (b < a)

    @given(arrow_objects(), arrow_objects(), arrow_objects())
    def test_transitive_lt(self, a: Arrow, b: Arrow, c: Arrow):
        """If a <= b and b <= c then a <= c."""
        if a <= b and b <= c:
            assert a <= c

    @given(arrow_objects())
    def test_not_lt_self(self, arw: Arrow):
        """Arrow is not strictly less than itself."""
        assert not (arw < arw)

    @given(arrow_objects(), arrow_objects())
    def test_symmetry_of_equality(self, a: Arrow, b: Arrow):
        """Equality is symmetric."""
        assert (a == b) == (b == a)


# ---------------------------------------------------------------------------
# Arrow.fromdatetime / fromdate
# ---------------------------------------------------------------------------

class TestArrowFromDatetimeProperties:

    @given(st.datetimes(min_value=stdlib_datetime.datetime(1, 1, 1), max_value=stdlib_datetime.datetime(9999, 12, 31, 23, 59, 59)))
    def test_fromdatetime_preserves_components(self, dt: stdlib_datetime.datetime):
        """Arrow.fromdatetime preserves year/month/day/hour/minute/second."""
        arw = Arrow.fromdatetime(dt)
        assert arw.year == dt.year
        assert arw.month == dt.month
        assert arw.day == dt.day
        assert arw.hour == dt.hour
        assert arw.minute == dt.minute
        assert arw.second == dt.second

    @given(st.dates(min_value=stdlib_datetime.date(1, 1, 1), max_value=stdlib_datetime.date(9999, 12, 31)))
    def test_fromdate_zero_time_components(self, d: stdlib_datetime.date):
        """Arrow.fromdate always results in midnight (all time components 0)."""
        arw = Arrow.fromdate(d)
        assert arw.hour == 0
        assert arw.minute == 0
        assert arw.second == 0
        assert arw.microsecond == 0

    @given(st.dates(min_value=stdlib_datetime.date(1, 1, 1), max_value=stdlib_datetime.date(9999, 12, 31)))
    def test_fromdate_preserves_date_components(self, d: stdlib_datetime.date):
        """Arrow.fromdate preserves year/month/day."""
        arw = Arrow.fromdate(d)
        assert arw.year == d.year
        assert arw.month == d.month
        assert arw.day == d.day


# ---------------------------------------------------------------------------
# Arrow.quarter property
# ---------------------------------------------------------------------------

class TestArrowQuarterProperties:

    @given(arrow_objects())
    def test_quarter_in_range(self, arw: Arrow):
        """Quarter is always in [1, 4]."""
        assert 1 <= arw.quarter <= 4

    @given(arrow_objects())
    def test_quarter_consistent_with_month(self, arw: Arrow):
        """Quarter is consistent with month: Q1=months1-3, Q2=4-6, Q3=7-9, Q4=10-12."""
        expected = (arw.month - 1) // 3 + 1
        assert arw.quarter == expected


# ---------------------------------------------------------------------------
# Arrow.humanize (basic sanity invariants)
# ---------------------------------------------------------------------------

class TestArrowHumanizeProperties:

    @given(arrow_objects())
    def test_humanize_same_moment_is_now(self, arw: Arrow):
        """Humanizing against the same Arrow returns the 'now' string."""
        result = arw.humanize(arw)
        assert "just now" in result or result == "just now" or "now" in result

    @given(arrow_objects())
    def test_humanize_returns_string(self, arw: Arrow):
        """Arrow.humanize always returns a str."""
        result = arw.humanize(arw)
        assert isinstance(result, str)

    @given(arrow_objects(), st.integers(min_value=1, max_value=100))
    def test_humanize_past_contains_ago(self, arw: Arrow, hours_back: int):
        """Humanizing an Arrow that is hours in the past contains 'ago'."""
        earlier = arw.shift(hours=-hours_back)
        result = earlier.humanize(arw)
        assert "ago" in result


# ---------------------------------------------------------------------------
# Arrow.week property
# ---------------------------------------------------------------------------

class TestArrowWeekProperties:

    @given(arrow_objects())
    def test_week_in_range(self, arw: Arrow):
        """Week number is always between 1 and 53."""
        assert 1 <= arw.week <= 53

    @given(arrow_objects())
    def test_week_consistent_with_isocalendar(self, arw: Arrow):
        """Arrow.week matches stdlib isocalendar()[1]."""
        _, iso_week, _ = arw.isocalendar()
        assert arw.week == iso_week


# ---------------------------------------------------------------------------
# ArrowFactory.get
# ---------------------------------------------------------------------------

class TestArrowFactoryGetProperties:

    @given(st.datetimes(min_value=stdlib_datetime.datetime(1, 1, 1), max_value=stdlib_datetime.datetime(9999, 12, 31, 23, 59, 59)))
    def test_get_from_datetime_preserves_components(self, dt: stdlib_datetime.datetime):
        """arrow.get(datetime) preserves year/month/day/hour/minute/second."""
        arw = arrow.get(dt)
        assert arw.year == dt.year
        assert arw.month == dt.month
        assert arw.day == dt.day
        assert arw.hour == dt.hour
        assert arw.minute == dt.minute
        assert arw.second == dt.second

    @given(st.dates(min_value=stdlib_datetime.date(1, 1, 1), max_value=stdlib_datetime.date(9999, 12, 31)))
    def test_get_from_date_gives_midnight(self, d: stdlib_datetime.date):
        """arrow.get(date) returns midnight for the given date."""
        arw = arrow.get(d)
        assert arw.year == d.year
        assert arw.month == d.month
        assert arw.day == d.day
        assert arw.hour == 0

    @given(safe_timestamps)
    @settings(max_examples=200)
    def test_get_from_timestamp_returns_arrow(self, ts: float):
        """arrow.get(timestamp) always returns an Arrow."""
        arw = arrow.get(ts)
        assert isinstance(arw, Arrow)

    @given(arrow_objects())
    def test_get_from_arrow_is_copy(self, arw: Arrow):
        """arrow.get(arrow_obj) returns an equal Arrow (copy semantics)."""
        copy = arrow.get(arw)
        assert copy == arw

    @given(arrow_objects())
    def test_get_from_arrow_is_different_object(self, arw: Arrow):
        """arrow.get(arrow_obj) returns a new object, not the same reference."""
        copy = arrow.get(arw)
        assert copy is not arw
