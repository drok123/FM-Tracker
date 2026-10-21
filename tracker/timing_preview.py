"""Offline preview of SLOOP ratchets and step nudges."""
from dataclasses import dataclass
from .sloop_details import synth_note_details, drum_lane_details

@dataclass(frozen=True)
class TimedHit:
    tick: int
    track: int
    note: int
    level: int
    velocity: int
    drum: bool

def preview_hits(pattern, track, nudges=None, rows=None):
    if track not in range(4):
        raise ValueError("invalid track")
    drums = track == 3
    steps = pattern.drum_steps if drums else pattern.synth_steps
    if drums and pattern.synth_steps or not drums and pattern.drum_steps:
        raise ValueError("wrong pattern type")
    if not drums and steps and steps[0].track != track:
        raise ValueError("wrong synth track")
    if nudges is not None and len(nudges) != 64:
        raise ValueError("expected 64 nudges")
    count = len(steps) if rows is None else rows
    if count < 0 or (count and not steps):
        raise ValueError("invalid rows")
    result = []
    for row in range(count):
        step = steps[row % len(steps)]
        nudge = 0 if nudges is None else nudges[step.index]
        if not -32 <= nudge <= 31:
            raise ValueError("invalid nudge")
        details = drum_lane_details(step) if drums else (
            synth_note_details(step) if step.time == 0 else ())
        for note, level, ratchets in details:
            for hit in range(ratchets):
                tick = row * 64 + nudge + hit * 64 // ratchets
                result.append(TimedHit(tick, track, note, level,
                                       0 if drums else step.velocity, drums))
    return sorted(result, key=lambda event: (event.tick, event.track, event.note))
