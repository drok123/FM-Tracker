"""Fine-tick host playback, independent of the firmware clock/audio.

Notes sustain until a retrigger, non-tie step, launch or stop. Instrument gates,
slides, locks, fill and swing are not emulated. Drum values are lane IDs.
"""
from dataclasses import dataclass
from .sloop_capture import ImportedPattern
from .launch import ScheduledLaunch, queue_launch, pop_due
from .timing_preview import TICKS_PER_ROW, TimedHit, step_hits

@dataclass(frozen=True)
class CapturedPlaybackEvent:
    row: int
    track: int
    kind: str
    value: int
    velocity: int = 0
    tick: int = 0
    level: int = 0

class CapturedPerformance:
    def __init__(self, phrases: dict[str, ImportedPattern], tracks: int = 4):
        if tracks != 4:
            raise ValueError("SLOOP has four tracks")
        self.phrases = dict(phrases)
        self.active: list[str | None] = [None] * tracks
        self.started = [0] * tracks  # absolute launch rows
        self.voices: list[set[int]] = [set() for _ in range(tracks)]
        self.pending: tuple[ScheduledLaunch, ...] = ()
        self.next_row = 0
        self.next_tick = 0
        self._step = [0] * tracks  # next local step, including loop passes
        self._hits: list[list[TimedHit]] = [[] for _ in range(tracks)]

    def queue(self, launch: ScheduledLaunch) -> None:
        if (not isinstance(launch.track, int) or not 0 <= launch.track < 4 or
                not isinstance(launch.at_row, int) or
                launch.at_row * TICKS_PER_ROW < self.next_tick):
            raise ValueError("invalid track or launch time")
        if launch.phrase is not None:
            if launch.phrase not in self.phrases:
                raise ValueError("unknown phrase")
            phrase = self.phrases[launch.phrase]
            if launch.track == 3 and (not phrase.drum_steps or phrase.synth_steps):
                raise ValueError("drum track requires drum phrase")
            if launch.track < 3 and (not phrase.synth_steps or phrase.drum_steps or
                                     any(s.track != launch.track for s in phrase.synth_steps)):
                raise ValueError("phrase belongs to another synth track")
        self.pending = queue_launch(self.pending, launch)

    @staticmethod
    def _event(tick, track, kind, value, velocity=0, level=0):
        return CapturedPlaybackEvent(tick // TICKS_PER_ROW, track, kind, value,
                                     velocity, tick, level)

    def _release(self, tick: int, track: int) -> list[CapturedPlaybackEvent]:
        events = [self._event(tick, track, "note_off", n)
                  for n in sorted(self.voices[track])]
        self.voices[track].clear()
        return events

    def _next_step(self, track):
        pattern = self.phrases[self.active[track]]
        steps = pattern.drum_steps if track == 3 else pattern.synth_steps
        local = self._step[track]
        index = local % len(steps)
        nudge = pattern.phrase.source.steps[index].nudge
        start = self.started[track] * TICKS_PER_ROW
        # A launch cannot emit a note in the past; subsequent early steps can
        # fire in the preceding row, including across a natural pattern loop.
        tick = max(start, start + local * TICKS_PER_ROW + nudge)
        return tick, steps[index]

    def advance(self, row: int) -> list[CapturedPlaybackEvent]:
        """Advance through the row's boundary (row * 64), inclusive."""
        if not isinstance(row, int) or row < 0:
            raise ValueError("invalid row")
        return self.advance_ticks(row * TICKS_PER_ROW)

    def advance_ticks(self, tick: int) -> list[CapturedPlaybackEvent]:
        """Consume events through an absolute fine tick, inclusive, once.

        Jump between due events so skipped transport calls remain lossless.
        Launches precede steps and ratchets at the same tick. New steps cancel
        remaining hits from the previous step, matching upstream step ownership.
        """
        if not isinstance(tick, int) or tick < 0 or tick < self.next_tick - 1:
            raise ValueError("cannot rewind or use an invalid tick")
        events: list[CapturedPlaybackEvent] = []
        while True:
            steps = {track: self._next_step(track)
                     for track, name in enumerate(self.active) if name is not None}
            times = [launch.at_row * TICKS_PER_ROW for launch in self.pending]
            times.extend(at for at, _ in steps.values())
            times.extend(hit.tick for hits in self._hits for hit in hits)
            if not times or min(times) > tick:
                break
            now = min(times)
            if now % TICKS_PER_ROW == 0:
                due, self.pending = pop_due(self.pending, now // TICKS_PER_ROW)
                for launch in due:
                    track = launch.track
                    events.extend(self._release(now, track))
                    self._hits[track] = []
                    self.active[track] = launch.phrase
                    self.started[track] = launch.at_row
                    self._step[track] = 0
            for track, name in enumerate(self.active):
                if name is None:
                    continue
                at, step = self._next_step(track)
                if at == now:
                    self._hits[track] = step_hits(step, track, at)
                    self._step[track] += 1
                    if track < 3 and step.time != 1:
                        events.extend(self._release(now, track))
                due_hits = [hit for hit in self._hits[track] if hit.tick == now]
                self._hits[track] = [hit for hit in self._hits[track] if hit.tick > now]
                for hit in due_hits:
                    if not hit.drum:
                        if hit.note in self.voices[track]:
                            events.append(self._event(now, track, "note_off", hit.note))
                        self.voices[track].add(hit.note)
                    events.append(self._event(now, track,
                                              "drum_hit" if hit.drum else "note_on",
                                              hit.note, hit.velocity, hit.level))
        self.next_tick = tick + 1
        self.next_row = tick // TICKS_PER_ROW + 1
        return sorted(events, key=lambda e: (e.tick, e.kind != "note_off", e.track))

    def stop(self) -> list[CapturedPlaybackEvent]:
        """Release at the first unconsumed tick and cancel all future work."""
        events = []
        for track in range(4):
            events.extend(self._release(self.next_tick, track))
        self.active = [None] * 4
        self._hits = [[] for _ in range(4)]
        self.pending = ()
        return events
