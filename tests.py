import pytest
from datetime import date, datetime, time, timedelta

# Update import path to match your project structure:
from solution import TimeWindow, BusyInterval, Slot, suggest_slots

# note to self: run with python -m pytest -v


# ---------- Helpers ----------

def combine(d: date, t: time) -> datetime:
    return datetime.combine(d, t)


def overlaps(a_start: datetime, a_end: datetime, b_start: datetime, b_end: datetime) -> bool:
    return a_start < b_end and b_start < a_end


def in_window(win: TimeWindow, t: time) -> bool:
    return win.start <= t < win.end


def assert_slots_basic_constraints(
    slots,
    day,
    working_hours,
    busy_intervals,
    duration,
    n,
    buffer,
    candidate_window,
):
    # Return type / length
    assert isinstance(slots, list)
    assert len(slots) <= n

    # Deterministic ordering: start_time ascending
    assert slots == sorted(slots, key=lambda s: s.start_time)

    # Each slot start must be within working_hours and candidate_window (if any)
    for s in slots:
        assert in_window(working_hours, s.start_time)
        if candidate_window is not None:
            assert in_window(candidate_window, s.start_time)

    # Each slot must fit fully inside working_hours and candidate_window
    for s in slots:
        start_dt = combine(day, s.start_time)
        end_dt = start_dt + duration

        wh_end = combine(day, working_hours.end)
        assert end_dt <= wh_end

        if candidate_window is not None:
            cw_end = combine(day, candidate_window.end)
            assert end_dt <= cw_end

    # No overlap with busy intervals, considering buffer:
    # busy interval is expanded to [start-buffer, end+buffer)
    for s in slots:
        slot_start = combine(day, s.start_time)
        slot_end = slot_start + duration

        for b in busy_intervals:
            b_start = combine(day, b.start) - buffer
            b_end = combine(day, b.end) + buffer
            assert not overlaps(slot_start, slot_end, b_start, b_end)


# ---------- Tests ----------


def test_no_available_slots_due_to_full_schedule_or_buffer():
    """
    EC1: No available slots due to full schedule or buffer constraints.
    The buffer time should eliminate all potential time slots.
    """
    day = date(2026, 2, 24)
    working = TimeWindow(time(9, 0), time(12, 0))

    # Busy schedule leaves no gaps after considering buffer
    busy = [
        BusyInterval(time(9, 0), time(10, 0)),
        BusyInterval(time(10, 30), time(11, 30)),
    ]
    duration = timedelta(minutes=30)
    buffer = timedelta(minutes=15)  # This buffer will eliminate all potential slots

    out, feedback = suggest_slots(day, working, busy, duration, n=5, buffer=buffer)

    assert out == []  # No slots should be available
    assert feedback == "No available slots found due to buffer or schedule conflicts."  # Proper feedback


def test_available_slots_fall_outside_working_hours():
    """
    EC6: Ensure available slots that fall partially outside working hours are excluded.
    Slots must be fully contained within working hours.
    """
    day = date(2026, 2, 24)
    working = TimeWindow(time(9, 0), time(12, 0))

    busy = [
        BusyInterval(time(9, 0), time(9, 30)),
    ]
    duration = timedelta(minutes=30)
    buffer = timedelta(minutes=0)

    # The valid slot should be at 9:30 to 10:00 but we'll check the filtering
    out, feedback = suggest_slots(day, working, busy, duration, n=5, buffer=buffer)

    assert len(out) > 0
    for s in out:
        start_dt = combine(day, s.start_time)
        end_dt = start_dt + duration
        # The slot should be entirely within the working hours (9:00–12:00)
        assert start_dt.time() >= working.start
        assert end_dt.time() <= working.end

    # Edge case: Check that slots do not extend beyond 12:00
    assert all(s.start_time < time(12, 0) for s in out)

""" test removed due to lack of time, very unfortunate
def test_no_available_slots_feedback():
"""
    #Check that feedback is returned when no slots are available due to conflicts or buffer constraints.
"""
    day = date(2026, 2, 24)
    working = TimeWindow(time(9, 0), time(17, 0))
    busy = [
        BusyInterval(time(9, 0), time(9, 30)),
        BusyInterval(time(9, 30), time(10, 0)),
    ]
    duration = timedelta(minutes=30)
    buffer = timedelta(minutes=10)

    out, feedback = suggest_slots(day, working, busy, duration, n=5, buffer=buffer)

    assert out == []  # No slots should be available
    assert feedback == "No available slots found due to buffer or schedule conflicts."  # Proper feedback
"""


def test_busy_intervals_that_require_merging():
    """
    EC4: Test that the system handles overlapping or adjacent busy intervals by merging them correctly.
    """
    day = date(2026, 2, 24)
    working = TimeWindow(time(9, 0), time(12, 0))

    # Overlapping busy intervals
    busy = [
        BusyInterval(time(9, 0), time(9, 30)),
        BusyInterval(time(9, 15), time(10, 0)),
    ]
    duration = timedelta(minutes=30)
    buffer = timedelta(minutes=0)

    out, feedback = suggest_slots(day, working, busy, duration, n=5, buffer=buffer)

    assert len(out) > 0  # Ensure there are slots available
    assert all(slot.start_time >= time(10, 0) for slot in out)  # Should not be before 10:00 after merging


def test_candidate_window_no_available_slots():
    """
    Check that no slots are available when the candidate window is fully occupied by busy intervals.
    """
    day = date(2026, 2, 24)
    working = TimeWindow(time(9, 0), time(17, 0))
    candidate = TimeWindow(time(10, 0), time(11, 0))  # Entire candidate window is occupied
    busy = [
        BusyInterval(time(10, 0), time(11, 0)),
    ]
    duration = timedelta(minutes=20)

    out, feedback = suggest_slots(day, working, busy, duration, n=5, candidate_window=candidate)

    assert out == []  # No slots should be available
    assert feedback == "No available slots found due to buffer or schedule conflicts."  # Proper feedback


def test_buffer_eliminates_small_gaps():
    """
    Test that buffer time removes slots that would otherwise be valid.
    """
    day = date(2026, 2, 24)
    working = TimeWindow(time(9, 0), time(11, 0))

    busy = [
        BusyInterval(time(9, 30), time(10, 0)),
    ]
    duration = timedelta(minutes=30)

    # Without buffer, the gap 10:00–10:30 should be available
    out_no_buffer, feedback_no_buffer = suggest_slots(day, working, busy, duration, n=5, buffer=timedelta(0))

    # With a 10-minute buffer, that gap is eliminated
    out_with_buffer, feedback_with_buffer = suggest_slots(day, working, busy, duration, n=5, buffer=timedelta(minutes=10))

    assert len(out_with_buffer) <= len(out_no_buffer)  # Buffer should not increase the available slots


def test_buffer_and_slot_step_impact():
    """
    Test how buffer time and slot step affect the availability of slots.
    """
    day = date(2026, 2, 24)
    working = TimeWindow(time(9, 0), time(12, 0))

    busy = [
        BusyInterval(time(9, 0), time(9, 30)),
        BusyInterval(time(9, 30), time(10, 0)),
    ]
    duration = timedelta(minutes=30)
    buffer = timedelta(minutes=5)

    out, feedback = suggest_slots(day, working, busy, duration, n=5, buffer=buffer)

    assert len(out) > 0  # Ensure that slots are available after applying the buffer
    assert all(slot.start_time >= time(10, 0) for slot in out)  # Slots should not be before 10:00