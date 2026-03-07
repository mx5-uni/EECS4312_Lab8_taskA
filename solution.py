## Student Name: Anna Maximova
## Student ID: 219815257

"""
Task A: Appointment Timeslot Recommender (Stub)

In this lab, you will design and implement an Appointment Slot Recommender using an LLM assistant
as your primary programming collaborator.

You are asked to implement a Python module that recommends available meeting slots within a
defined working window.

The system must:
  • Accept working hours (start and end time).
  • Accept a list of existing busy intervals.
  • Accept a required meeting duration.
  • Accept an optional buffer time between meetings.
  • Optionally restrict suggestions to a candidate time window.
  • Return chronologically ordered appointment slots that satisfy all constraints.

The system must ensure that:
  • Suggested slots fall within working hours.
  • Suggested slots do not overlap busy intervals.
  • Buffer time is respected when evaluating availability.
  • Output ordering is deterministic under identical inputs.

The module must preserve the following invariants:
  • Returned slots must be at least as long as the required duration.
  • No returned slot may violate buffer constraints.
  • The returned list must reflect the current system state.

The system must correctly handle non-trivial scenarios such as:
  • Adjacent busy intervals.
  • Very small gaps between meetings.
  • Buffers eliminating otherwise valid availability.
  • Overlapping or unsorted busy intervals.
  • A meeting duration longer than any available gap.
  • No availability within the working window.

Output:
  The output consists of the next N valid appointment suggestions in chronological order.
  Behavior must be deterministic under ties (if any).

See the lab handout for full requirements.
"""

from dataclasses import dataclass
from datetime import date, datetime, timedelta, time
from typing import List, Optional, Tuple


# ---------------- Data Models ----------------

@dataclass(frozen=True)
class TimeWindow:
    """
    A daily time window.
    Assumption (unless stated otherwise in handout): non-wrapping window where start < end.
    """
    start: time
    end: time


@dataclass(frozen=True)
class BusyInterval:
    """
    A busy interval on the given day.
    Invariant: start < end
    """
    start: time
    end: time


@dataclass(frozen=True)
class Slot:
    """
    A recommended appointment slot.

    start_time is a time-of-day within the working window.
    Deterministic ordering: sort by start_time ascending.
    """
    start_time: time


class InfeasibleSchedule(Exception):
    """Raised when no valid slots can be produced (if required by handout)."""
    pass

# ---------------- Helper Functions ----------------

def _combine(day: date, t: time) -> datetime:
    return datetime.combine(day, t)


def _merge_intervals(intervals):
    """Merge overlapping or adjacent intervals."""
    if not intervals:
        return []

    intervals.sort(key=lambda x: x[0])
    merged = [intervals[0]]

    for start, end in intervals[1:]:
        last_start, last_end = merged[-1]

        if start <= last_end:  # overlap OR adjacency
            merged[-1] = (last_start, max(last_end, end))
        else:
            merged.append((start, end))

    return merged


def _intersect(a_start, a_end, b_start, b_end):
    start = max(a_start, b_start)
    end = min(a_end, b_end)
    if start < end:
        return (start, end)
    return None


# ---------------- Core Function ----------------

def suggest_slots(
    day: date,
    working_hours: TimeWindow,
    busy_intervals: List[BusyInterval],
    duration: timedelta,
    n: int,
    buffer: timedelta = timedelta(0),
    candidate_window: Optional[TimeWindow] = None
) -> List[Slot]:
    """
    Suggest up to the next n valid appointment slots (start times) for the given day.

    Args:
        day: the calendar day for which to suggest slots.
        working_hours: the allowed working window for meetings (start < end).
        busy_intervals: list of busy time intervals (may be overlapping / unsorted).
        duration: required meeting length (must be > 0).
        n: maximum number of slot suggestions to return (n >= 0).
        buffer: optional buffer time required between meetings (buffer >= 0).
        candidate_window: optional extra restriction on suggestions (must lie within this window too).

    Returns:
        A list of Slot objects, sorted by start_time ascending, deterministic under identical inputs.
        If no suitable time slots are available, return an empty list.

    Notes:
        - Suggested slots must fall within working_hours (and candidate_window if provided).
        - Suggested slots must not overlap busy_intervals, considering buffer time.
        - You are free to choose internal representation; inputs use time-of-day.
        - See lab handout for required slot granularity (e.g., 5-min/15-min steps), if any.
    """

    if duration <= timedelta(0):
        raise ValueError("duration must be positive")

    if n <= 0:
        return []

    STEP = timedelta(minutes=5)

    # ---- Working window ----
    working_start = _combine(day, working_hours.start)
    working_end = _combine(day, working_hours.end)

    # ---- Candidate window ----
    if candidate_window:
        cand_start = _combine(day, candidate_window.start)
        cand_end = _combine(day, candidate_window.end)
    else:
        cand_start = working_start
        cand_end = working_end

    # ensure candidate inside working
    cand_start = max(cand_start, working_start)
    cand_end = min(cand_end, working_end)

    # ---- Convert busy intervals ----
    busy_dt = []
    for b in busy_intervals:
        start = _combine(day, b.start)
        end = _combine(day, b.end)

        # apply buffer
        start -= buffer
        end += buffer

        busy_dt.append((start, end))

    # ---- Normalize busy intervals ----
    busy_dt = _merge_intervals(busy_dt)

    # ---- Clip busy to working window ----
    clipped_busy = []
    for s, e in busy_dt:
        if e <= working_start or s >= working_end:
            continue
        clipped_busy.append((max(s, working_start), min(e, working_end)))

    busy_dt = _merge_intervals(clipped_busy)

    # ---- Compute free gaps ----
    free_gaps = []

    prev = working_start

    for s, e in busy_dt:
        if prev < s:
            free_gaps.append((prev, s))
        prev = max(prev, e)

    if prev < working_end:
        free_gaps.append((prev, working_end))

    # ---- Apply candidate window restriction ----
    candidate_gaps = []
    for s, e in free_gaps:
        inter = _intersect(s, e, cand_start, cand_end)
        if inter:
            candidate_gaps.append(inter)

    # ---- Generate slots ----
    slots = []

    for gap_start, gap_end in candidate_gaps:

        t = gap_start

        while t + duration <= gap_end:
            slots.append(Slot(start_time=t.time()))

            if len(slots) >= n:
                return sorted(slots, key=lambda s: s.start_time)

            t += STEP

    return sorted(slots, key=lambda s: s.start_time)
