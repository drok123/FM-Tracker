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
