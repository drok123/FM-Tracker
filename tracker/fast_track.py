"""Lossless intermediate capture model for Fast Track (host-side prototype).

This is not a decoder for SLOOP's binary project format. A future firmware
adapter must map its actual structures into these typed values.
"""
from dataclasses import dataclass, replace
from typing import Optional
from .engine import Cell, Command

@dataclass(frozen=True)
class SourceStep:
    notes: tuple[int, ...] = ()
    velocity: int = 100
    ratchet: int = 1
    nudge: int = 0
    tie: bool = False
    slide: bool = False
    fill: str = "normal"
    locks: tuple[tuple[int, int], ...] = ()
    drum_hits: tuple[tuple[int, int, int], ...] = ()
    # Lossless SLOOP fields. The editor's Cell remains a deliberately simple
    # first-note view; these fields always stay attached to the source row.
    time: int = 0
    flags: int = 0
    levels: int = 0
    ratchets: int = 0
    fill_condition: int = 0
    drum_on: int = 0
    source_track: int | None = None
    source_index: int | None = None

@dataclass(frozen=True)
class SourcePattern:
    steps: tuple[SourceStep, ...]
    division: str = "1/16"
    swing: int = 0

@dataclass(frozen=True)
class FastTrackPhrase:
    source: SourcePattern
    tracker_rows: tuple[Cell, ...]
    extras: tuple[tuple[Command, ...], ...]
    revision: int = 0

def capture(source: SourcePattern) -> FastTrackPhrase:
    if not 1 <= len(source.steps) <= 64:
        raise ValueError("source pattern must have 1..64 steps")
    rows = []
    for step in source.steps:
        if len(step.notes) > 4 or any(not 0 <= n <= 127 for n in step.notes):
            raise ValueError("invalid source notes")
        if step.time not in (0, 1, 2) or not 0 <= step.flags <= 255:
            raise ValueError("invalid SLOOP step metadata")
        if (not 0 <= step.levels <= 0xFFFFFFFF or
                not 0 <= step.ratchets <= 0xFFFFFFFF or
                not 0 <= step.drum_on <= 0xFFFFFF):
            raise ValueError("invalid packed SLOOP step data")
        if step.fill_condition not in (0, 1, 2, 3):
            raise ValueError("invalid fill condition")
        if any(not 0 <= parameter <= 255 or not -8192 <= value <= 8191
               for parameter, value in step.locks):
            raise ValueError("invalid parameter lock")
        rows.append(Cell(note=step.notes[0] if step.notes else None,
                         volume=step.velocity if step.notes else None))
    return FastTrackPhrase(source, tuple(rows), tuple(() for _ in rows))

def set_commands(phrase: FastTrackPhrase, row: int, commands: tuple[Command, ...]) -> FastTrackPhrase:
    if not 0 <= row < len(phrase.tracker_rows):
        raise IndexError(row)
    extras = list(phrase.extras)
    extras[row] = commands
    return replace(phrase, extras=tuple(extras), revision=phrase.revision + 1)

def refresh_source(phrase: FastTrackPhrase, source: SourcePattern) -> FastTrackPhrase:
    """Re-capture note data while retaining commands at matching row indices."""
    updated = capture(source)
    extras = tuple(phrase.extras[i] if i < len(phrase.extras) else ()
                   for i in range(len(updated.tracker_rows)))
    return replace(updated, extras=extras, revision=phrase.revision + 1)

def tracker_view(phrase: FastTrackPhrase) -> tuple[Cell, ...]:
    return tuple(replace(cell, commands=commands)
                 for cell, commands in zip(phrase.tracker_rows, phrase.extras))
