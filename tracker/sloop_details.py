"""Lossless accessors for SLOOP's packed per-note/per-lane dynamics.

Based on upstream firmware/src/core.h: each level and ratchet occupies
two bits, and ratchet count is encoded as count minus one.
"""
from .sloop_protocol import SynthStep, DrumStep

def synth_note_details(step: SynthStep) -> tuple[tuple[int, int, int], ...]:
    if len(step.notes) > 4:
        raise ValueError("too many synth notes")
    return tuple((note, (step.levels >> (2*i)) & 3,
                  1 + ((step.ratchets >> (2*i)) & 3))
                 for i, note in enumerate(step.notes))

def drum_lane_details(step: DrumStep) -> tuple[tuple[int, int, int], ...]:
    return tuple((lane, (step.levels >> (2*lane)) & 3,
                  1 + ((step.ratchets >> (2*lane)) & 3))
                 for lane in range(16) if step.on & (1 << lane))

def level_velocity(level: int, base: int) -> int:
    """SLOOP's LV_NORM/GHOST/SOFT/HARD velocity mapping from drums.c."""
    if not 0 <= level <= 3 or not 0 <= base <= 127:
        raise ValueError("invalid level or base velocity")
    return base if level == 0 else (0, 42, 72, 127)[level]

def synth_note_velocities(step: SynthStep) -> tuple[tuple[int, int, int], ...]:
    base = 127 if step.flags & 1 else (step.velocity or 96)
    return tuple((note, level, ratchets,
                  level_velocity(level, base))
                 for note, level, ratchets in synth_note_details(step))

def drum_lane_velocities(step: DrumStep) -> tuple[tuple[int, int, int, int], ...]:
    return tuple((lane, level, ratchets, level_velocity(level, 100))
                 for lane, level, ratchets in drum_lane_details(step))
