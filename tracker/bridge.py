"""Fast Track event adapter: expand captured SLOOP-like steps without data loss.

Host reference only. SourcePattern is our own model, not an upstream decoder.
All timing uses integer subticks (64 per row); actual SLOOP clock mapping TBD.
"""
from dataclasses import dataclass
from .fast_track import FastTrackPhrase

@dataclass(frozen=True)
class CapturedEvent:
    subtick: int
    track: int
    kind: str
    note_or_lane: int
    velocity: int
    repeat_index: int = 0

def render_capture(phrase: FastTrackPhrase, track: int = 0, subticks_per_row: int = 64) -> list[CapturedEvent]:
    if subticks_per_row <= 0:
        raise ValueError("subticks_per_row must be positive")
    result = []
    for row, step in enumerate(phrase.source.steps):
        if not 1 <= step.ratchet <= 16:
            raise ValueError("ratchet must be 1..16")
        if not 0 <= step.velocity <= 127:
            raise ValueError("velocity must be 0..127")
        start = row * subticks_per_row + step.nudge
        if start < 0:
            raise ValueError("nudge before pattern start")
        for repeat in range(step.ratchet):
            at = start + (repeat * subticks_per_row) // step.ratchet
            for note in step.notes:
                result.append(CapturedEvent(at, track, "note_on", note, step.velocity, repeat))
        for lane, level, ratchet in step.drum_hits:
            if not 0 <= lane < 16 or not 0 <= level <= 127 or not 1 <= ratchet <= 16:
                raise ValueError("invalid drum hit")
            for repeat in range(ratchet):
                at = start + (repeat * subticks_per_row) // ratchet
                result.append(CapturedEvent(at, track, "drum_hit", lane, level, repeat))
    return sorted(result, key=lambda e: (e.subtick, e.track, e.kind, e.note_or_lane, e.repeat_index))
