"""Tick-accurate tracker event compiler, independent of FM-1 hardware."""
from dataclasses import dataclass
from typing import Optional

@dataclass(frozen=True)
class Command:
    code: str
    value: int

@dataclass(frozen=True)
class Cell:
    note: Optional[int] = None
    instrument: Optional[int] = None
    volume: Optional[int] = None
    commands: tuple[Command, ...] = ()

@dataclass(frozen=True)
class TrackerEvent:
    tick: int
    track: int
    kind: str
    value: int
    instrument: Optional[int] = None

def compile_pattern(tracks: list[list[Cell]], rows: int = 64, ticks_per_row: int = 6) -> list[TrackerEvent]:
    """Supported commands: Rxx retrigger every xx ticks, Cxx probability 0..100.

    Probability is deterministic across renders using an integer mixer; C00 never
    triggers and C64 always triggers. Effect events may be extended later.
    """
    if rows < 0 or ticks_per_row <= 0:
        raise ValueError("invalid timing")
    events: list[TrackerEvent] = []
    for track_id, cells in enumerate(tracks):
        if not cells:
            continue
        for row in range(rows):
            cell = cells[row % len(cells)]
            if cell.note is None:
                continue
            if not 0 <= cell.note <= 127:
                raise ValueError("note must be 0..127")
            if cell.volume is not None and not 0 <= cell.volume <= 127:
                raise ValueError("volume must be 0..127")
            retrigger = 0
            probability = 100
            for command in cell.commands:
                if command.code == "R":
                    if not 1 <= command.value < ticks_per_row:
                        raise ValueError("R interval must be within row")
                    retrigger = command.value
                elif command.code == "C":
                    if not 0 <= command.value <= 100:
                        raise ValueError("C probability must be 0..100")
                    probability = command.value
                else:
                    raise ValueError("unsupported command: " + command.code)
            # Stable per-row pseudo-random value; independent of Python hash seed.
            roll = ((row * 1103515245 + track_id * 12345 + 1013904223) & 0xffffffff) % 100
            if roll >= probability:
                continue
            start = row * ticks_per_row
            for offset in range(0, ticks_per_row, retrigger or ticks_per_row):
                events.append(TrackerEvent(start + offset, track_id, "note_on", cell.note, cell.instrument))
                if cell.volume is not None:
                    events.append(TrackerEvent(start + offset, track_id, "volume", cell.volume, cell.instrument))
    return sorted(events, key=lambda e: (e.tick, e.track, 0 if e.kind == "volume" else 1))
