"""Independent per-track phrase chains, compiled on the host.

A chain entry has its own duration and repetition count. Track chains advance
independently; shorter chains may loop while longer chains continue.
"""
from dataclasses import dataclass
from .engine import Cell, TrackerEvent, compile_pattern

@dataclass(frozen=True)
class PhraseRef:
    name: str | None
    rows: int
    repeats: int = 1
    transpose: int = 0

@dataclass(frozen=True)
class TrackChain:
    entries: tuple[PhraseRef, ...]
    loop: bool = False

@dataclass(frozen=True)
class ChainSong:
    phrases: dict[str, tuple[Cell, ...]]
    tracks: tuple[TrackChain, ...]
    total_rows: int
    ticks_per_row: int = 6

def compile_chains(song: ChainSong) -> list[TrackerEvent]:
    if song.total_rows < 0 or song.ticks_per_row <= 0:
        raise ValueError("invalid song timing")
    output: list[TrackerEvent] = []
    for track_id, chain in enumerate(song.tracks):
        timeline: list[tuple[PhraseRef, int]] = []
        for entry in chain.entries:
            if entry.rows <= 0 or entry.repeats <= 0:
                raise ValueError("entry rows and repeats must be positive")
            if entry.name is not None and entry.name not in song.phrases:
                raise ValueError("missing phrase: " + entry.name)
            for _ in range(entry.repeats):
                timeline.append((entry, entry.rows))
        if not timeline:
            continue
        chain_length = sum(rows for _, rows in timeline)
        cursor = 0
        while cursor < song.total_rows:
            for entry, duration in timeline:
                if cursor >= song.total_rows:
                    break
                span = min(duration, song.total_rows - cursor)
                if entry.name is not None and song.phrases[entry.name]:
                    shifted = []
                    for cell in song.phrases[entry.name]:
                        note = None if cell.note is None else cell.note + entry.transpose
                        if note is not None and not 0 <= note <= 127:
                            raise ValueError("transposition out of MIDI range")
                        shifted.append(Cell(note, cell.instrument, cell.volume, cell.commands))
                    events = compile_pattern([shifted], rows=span, ticks_per_row=song.ticks_per_row)
                    output.extend(TrackerEvent(cursor * song.ticks_per_row + event.tick,
                                               track_id, event.kind, event.value, event.instrument)
                                  for event in events)
                cursor += span
            if not chain.loop:
                break
            if chain_length == 0:
                break
    return sorted(output, key=lambda e: (e.tick, e.track, 0 if e.kind == "volume" else 1))
