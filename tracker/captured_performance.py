"""Row-based performance engine for imported SLOOP phrases.

Host reference only: emits abstract synth note and drum trigger events.
Does not implement SLOOP audio ISR, parameter locks, ratchet timing or slides.
"""
from dataclasses import dataclass
from .sloop_capture import ImportedPattern
from .launch import ScheduledLaunch, queue_launch, pop_due

@dataclass(frozen=True)
class CapturedPlaybackEvent:
    row: int
    track: int
    kind: str
    value: int
    velocity: int = 0

class CapturedPerformance:
    def __init__(self, phrases: dict[str, ImportedPattern], tracks: int = 4):
        if tracks != 4:
            raise ValueError("SLOOP has four tracks")
        self.phrases = phrases
        self.active: list[str | None] = [None] * tracks
        self.started = [0] * tracks
        self.voices: list[set[int]] = [set() for _ in range(tracks)]
        self.pending: tuple[ScheduledLaunch, ...] = ()
        self.next_row = 0

    def queue(self, launch: ScheduledLaunch) -> None:
        if not 0 <= launch.track < 4 or launch.at_row < self.next_row:
            raise ValueError("invalid track or launch time")
        if launch.phrase is not None:
            if launch.phrase not in self.phrases:
                raise ValueError("unknown phrase")
            phrase = self.phrases[launch.phrase]
            if launch.track == 3 and not phrase.drum_steps:
                raise ValueError("drum track requires drum phrase")
            if launch.track < 3 and (not phrase.synth_steps or
                                     phrase.synth_steps[0].track != launch.track):
                raise ValueError("phrase belongs to another synth track")
        self.pending = queue_launch(self.pending, launch)

    def _release(self, row: int, track: int) -> list[CapturedPlaybackEvent]:
        events = [CapturedPlaybackEvent(row, track, "note_off", n)
                  for n in sorted(self.voices[track])]
        self.voices[track].clear()
        return events

    def advance(self, row: int) -> list[CapturedPlaybackEvent]:
        if row < self.next_row - 1:
            raise ValueError("cannot rewind")
        events: list[CapturedPlaybackEvent] = []
        while self.next_row <= row:
            now = self.next_row
            due, self.pending = pop_due(self.pending, now)
            for launch in due:
                events.extend(self._release(now, launch.track))
                self.active[launch.track] = launch.phrase
                self.started[launch.track] = now
            for track, name in enumerate(self.active):
                if name is None:
                    continue
                imported = self.phrases[name]
                if track == 3:
                    steps = imported.drum_steps
                    if not steps:
                        continue
                    step = steps[(now - self.started[track]) % len(steps)]
                    for lane in range(16):
                        if step.on & (1 << lane):
                            events.append(CapturedPlaybackEvent(now, track, "drum_hit", lane))
                    continue
                steps = imported.synth_steps
                if not steps:
                    continue
                step = steps[(now - self.started[track]) % len(steps)]
                if step.time == 1:  # tie sustains current notes
                    continue
                events.extend(self._release(now, track))
                if step.time == 0:
                    for note in step.notes:
                        events.append(CapturedPlaybackEvent(now, track, "note_on",
                                                            note, step.velocity))
                        self.voices[track].add(note)
            self.next_row += 1
        return events

    def stop(self) -> list[CapturedPlaybackEvent]:
        events = []
        for track in range(4):
            events.extend(self._release(self.next_row, track))
        self.active = [None] * 4
        self.pending = ()
        return events
