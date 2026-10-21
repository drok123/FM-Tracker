"""Portable deterministic tracker event scheduler (prototype)."""
from dataclasses import dataclass
from typing import Optional

@dataclass(frozen=True)
class Step:
    note: Optional[int] = None
    instrument: Optional[int] = None
    volume: Optional[int] = None

@dataclass(frozen=True)
class Event:
    tick: int
    track: int
    note: int
    instrument: Optional[int]
    volume: Optional[int]

def schedule(patterns: list[list[Step]], ticks_per_row: int = 6, rows: int = 64) -> list[Event]:
    """Schedule note-on events, cycling each track's own row length."""
    if ticks_per_row <= 0 or rows < 0:
        raise ValueError("invalid timing")
    events = []
    for track, pattern in enumerate(patterns):
        if not pattern:
            continue
        for row in range(rows):
            step = pattern[row % len(pattern)]
            if step.note is not None:
                if not 0 <= step.note <= 127:
                    raise ValueError("MIDI note out of range")
                events.append(Event(row * ticks_per_row, track, step.note, step.instrument, step.volume))
    return sorted(events, key=lambda e: (e.tick, e.track))
