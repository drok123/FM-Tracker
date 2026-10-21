"""Assemble parsed SLOOP step replies into the Fast Track source model.

Read-only projection: retain raw parsed replies alongside the editable phrase
because the prototype SourceStep cannot express all per-note level/ratchet bits.
"""
from dataclasses import dataclass
from .fast_track import SourceStep, SourcePattern, FastTrackPhrase, capture
from .sloop_protocol import SynthStep, DrumStep

def _validate_nudges(nudges):
    if nudges is not None and (len(nudges) != 64 or
                               any(not isinstance(n, int) or not -32 <= n <= 31
                                   for n in nudges)):
        raise ValueError("nudges must have 64 integers in -32..31")

@dataclass(frozen=True)
class ImportedPattern:
    phrase: FastTrackPhrase
    synth_steps: tuple[SynthStep, ...]
    drum_steps: tuple[DrumStep, ...]

def import_synth_pattern(steps: tuple[SynthStep, ...], *,
                         nudges: tuple[int, ...] | None = None,
                         fills: tuple[int, ...] | None = None) -> ImportedPattern:
    if not steps:
        raise ValueError("no steps")
    track = steps[0].track
    if not 0 <= track < 3 or any(s.track != track for s in steps):
        raise ValueError("mixed or invalid synth tracks")
    indices = [s.index for s in steps]
    if sorted(indices) != list(range(len(steps))):
        raise ValueError("steps must cover contiguous indices from zero")
    _validate_nudges(nudges)
    if fills is not None and (len(fills) != 64 or any(f not in (0, 1, 2, 3) for f in fills)):
        raise ValueError("fills must have 64 valid entries")
    ordered = tuple(sorted(steps, key=lambda s: s.index))
    source = SourcePattern(tuple(SourceStep(
        notes=s.notes if s.time == 0 else (),
        velocity=s.velocity,
        nudge=nudges[s.index] if nudges is not None else 0,
        tie=s.time == 1,
        slide=bool(s.flags & 2),
        fill=("normal", "fill", "not_fill", "normal")[fills[s.index]]
             if fills is not None else "normal"
    ) for s in ordered))
    return ImportedPattern(capture(source), ordered, ())

def import_drum_pattern(steps: tuple[DrumStep, ...], *,
                        nudges: tuple[int, ...] | None = None) -> ImportedPattern:
    if not steps:
        raise ValueError("no steps")
    _validate_nudges(nudges)
    indices = [s.index for s in steps]
    if sorted(indices) != list(range(len(steps))):
        raise ValueError("steps must cover contiguous indices from zero")
    ordered = tuple(sorted(steps, key=lambda s: s.index))
    source = SourcePattern(tuple(SourceStep(
        nudge=nudges[s.index] if nudges is not None else 0,
        drum_hits=tuple((lane, (s.levels >> (2*lane)) & 3,
                         1 + ((s.ratchets >> (2*lane)) & 3))
                        for lane in range(16) if s.on & (1 << lane))
    ) for s in ordered))
    return ImportedPattern(capture(source), (), ordered)
