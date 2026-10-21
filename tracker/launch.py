"""Pure host-side quantized launch planner.

Rows are absolute transport rows. Scheduling does not mutate a running
sequencer or fire notes; the future firmware adapter owns playback.
"""
from dataclasses import dataclass
from typing import Literal

Quantum = Literal["row", "beat", "bar", "phrase"]

@dataclass(frozen=True)
class LaunchRequest:
    track: int
    phrase: str | None
    requested_row: int
    quantum: Quantum = "bar"

@dataclass(frozen=True)
class ScheduledLaunch:
    track: int
    phrase: str | None
    at_row: int

def quantize_row(row: int, quantum: Quantum, *, rows_per_beat: int = 4,
                 beats_per_bar: int = 4, phrase_rows: int = 16) -> int:
    if row < 0 or min(rows_per_beat, beats_per_bar, phrase_rows) <= 0:
        raise ValueError("invalid transport or grid")
    grids = {"row": 1, "beat": rows_per_beat,
             "bar": rows_per_beat * beats_per_bar, "phrase": phrase_rows}
    if quantum not in grids:
        raise ValueError("unsupported launch quantum")
    grid = grids[quantum]
    # Inclusive: a request exactly on a boundary can start there.
    return ((row + grid - 1) // grid) * grid

def schedule_launch(request: LaunchRequest, *, rows_per_beat: int = 4,
                    beats_per_bar: int = 4, phrase_rows: int = 16) -> ScheduledLaunch:
    if request.track < 0:
        raise ValueError("invalid track")
    return ScheduledLaunch(request.track, request.phrase,
                           quantize_row(request.requested_row, request.quantum,
                                        rows_per_beat=rows_per_beat,
                                        beats_per_bar=beats_per_bar,
                                        phrase_rows=phrase_rows))

def queue_launch(pending: tuple[ScheduledLaunch, ...], launch: ScheduledLaunch) -> tuple[ScheduledLaunch, ...]:
    """Last queued launch wins per track, including an explicit stop (None)."""
    return tuple(item for item in pending if item.track != launch.track) + (launch,)

def pop_due(pending: tuple[ScheduledLaunch, ...], current_row: int
            ) -> tuple[tuple[ScheduledLaunch, ...], tuple[ScheduledLaunch, ...]]:
    if current_row < 0:
        raise ValueError("invalid current row")
    due = tuple(item for item in pending if item.at_row <= current_row)
    future = tuple(item for item in pending if item.at_row > current_row)
    return due, future
