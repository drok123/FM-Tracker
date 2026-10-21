"""Fast Track host-side phrase-chain arranger.

Phrase IDs refer to reusable patterns; no audio voices are allocated here.
Each song position has a fixed duration in rows. Phrase rows wrap independently.
"""
from dataclasses import dataclass
from .engine import Cell, TrackerEvent, compile_pattern

@dataclass(frozen=True)
class ChainSlot:
    phrase: str | None
    transpose: int = 0
    muted: bool = False

@dataclass(frozen=True)
class SongPosition:
    slots: tuple[ChainSlot, ...]
    rows: int = 16

@dataclass(frozen=True)
class Arrangement:
    phrases: dict[str, tuple[Cell, ...]]
    positions: tuple[SongPosition, ...]
    ticks_per_row: int = 6

def compile_arrangement(song: Arrangement) -> list[TrackerEvent]:
    if song.ticks_per_row <= 0:
        raise ValueError("ticks_per_row must be positive")
    if not song.positions:
        return []
    track_count = len(song.positions[0].slots)
    output: list[TrackerEvent] = []
    offset = 0
    for position in song.positions:
        if position.rows <= 0:
            raise ValueError("position rows must be positive")
        if len(position.slots) != track_count:
            raise ValueError("all positions must have same track count")
        for track, slot in enumerate(position.slots):
            if slot.muted or slot.phrase is None:
                continue
            if slot.phrase not in song.phrases:
                raise ValueError("missing phrase: " + slot.phrase)
            cells = song.phrases[slot.phrase]
            if not cells:
                continue
            # Transpose notes, but never alter the reusable source phrase.
            shifted = []
            for cell in cells:
                note = None if cell.note is None else cell.note + slot.transpose
                if note is not None and not 0 <= note <= 127:
                    raise ValueError("transposition out of MIDI note range")
                shifted.append(Cell(note, cell.instrument, cell.volume, cell.commands))
            events = compile_pattern([shifted], rows=position.rows, ticks_per_row=song.ticks_per_row)
            output.extend(TrackerEvent(offset + event.tick, track, event.kind,
                                       event.value, event.instrument) for event in events)
        offset += position.rows * song.ticks_per_row
    return sorted(output, key=lambda e: (e.tick, e.track, 0 if e.kind == "volume" else 1))
