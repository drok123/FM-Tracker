"""Offline preview of SLOOP ratchets and step nudges."""
from dataclasses import dataclass
from .sloop_details import synth_note_velocities, drum_lane_velocities
from .sloop_capture import _validate_nudges

TICKS_PER_ROW = 64

@dataclass(frozen=True)
class TimedHit:
    tick: int
    track: int
    note: int
    level: int
    velocity: int
    drum: bool
    ratchets: int = 1
    hit_index: int = 0

def step_hits(step, track, start):
    """Shared ideal-grid expansion; start includes the step's nudge."""
    drums = track == 3
    details = drum_lane_velocities(step) if drums else (
        synth_note_velocities(step) if step.time == 0 else ())
    return sorted((TimedHit(start + hit * TICKS_PER_ROW // ratchets,
                            track, note, level, velocity, drums,
                            ratchets, hit)
                   for note, level, ratchets, velocity in details
                   for hit in range(ratchets)),
                  key=lambda event: (event.tick, event.track, event.note))

def preview_hits(pattern, track, nudges=None, rows=None):
    if track not in range(4):
        raise ValueError("invalid track")
    drums = track == 3
    steps = pattern.drum_steps if drums else pattern.synth_steps
    if drums and pattern.synth_steps or not drums and pattern.drum_steps:
        raise ValueError("wrong pattern type")
    if not drums and steps and steps[0].track != track:
        raise ValueError("wrong synth track")
    _validate_nudges(nudges)
    count = len(steps) if rows is None else rows
    if count < 0 or (count and not steps):
        raise ValueError("invalid rows")
    result = []
    for row in range(count):
        step = steps[row % len(steps)]
        nudge = (pattern.phrase.source.steps[step.index].nudge if nudges is None
                 else nudges[step.index])
        result.extend(step_hits(step, track, row * TICKS_PER_ROW + nudge))
    return sorted(result, key=lambda event: (event.tick, event.track, event.note))
