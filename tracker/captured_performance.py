"""Fine-tick host playback, independent of the firmware clock/audio.

Notes honor the configured SLOOP gate, ties, per-step locks and fill condition.
Slide/glide engine behavior remains outside this abstract-event reference.
Drum values are lane IDs.
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
    parameter: int | None = None

class CapturedPerformance:
    def __init__(self, phrases: dict[str, ImportedPattern], tracks: int = 4,
                 gate: int | tuple[int, int, int] = 128, fill: bool = False):
        if tracks != 4:
            raise ValueError("SLOOP has four tracks")
        gates = (gate,) * 3 if isinstance(gate, int) else tuple(gate)
        if len(gates) != 3 or any(not isinstance(value, int) or not 0 <= value <= 128
                                  for value in gates):
            raise ValueError("synth gates must be three values in 0..128")
        if not isinstance(fill, bool):
            raise ValueError("fill must be boolean")
        self.phrases = dict(phrases)
        self.active: list[str | None] = [None] * tracks
        self.started = [0] * tracks  # absolute launch rows
        self._track_transpose = [0] * tracks
        self.gates = gates
        self.fill = fill
        self.voices: list[set[int]] = [set() for _ in range(tracks)]
        self.pending: tuple[ScheduledLaunch, ...] = ()
        self.next_row = 0
        self.next_tick = 0
        self._step = [0] * tracks  # next local step, including loop passes
        self._hits: list[list[TimedHit]] = [[] for _ in range(tracks)]
        self._note_offs: list[dict[int, int]] = [{} for _ in range(tracks)]
        self._active_locks: list[dict[int, int]] = [{} for _ in range(tracks)]

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
            if launch.track == 3 and launch.transpose:
                raise ValueError("drum phrases cannot be transposed")
            if launch.track < 3 and (not phrase.synth_steps or phrase.drum_steps or
                                     any(s.track != launch.track for s in phrase.synth_steps)):
                raise ValueError("phrase belongs to another synth track")
            if launch.track < 3 and any(
                    not 0 <= note + launch.transpose <= 127
                    for step in phrase.synth_steps for note in step.notes):
                raise ValueError("transposition outside MIDI note range")
        self.pending = queue_launch(self.pending, launch)

    @staticmethod
    def _event(tick, track, kind, value, velocity=0, level=0):
        return CapturedPlaybackEvent(tick // TICKS_PER_ROW, track, kind, value,
                                     velocity, tick, level)

    def _release(self, tick: int, track: int) -> list[CapturedPlaybackEvent]:
        events = [self._event(tick, track, "note_off", n)
                  for n in sorted(self.voices[track])]
        self.voices[track].clear()
        self._note_offs[track].clear()
        return events

    def _restore_locks(self, tick, track):
        events = [CapturedPlaybackEvent(tick // TICKS_PER_ROW, track,
                                       "lock_restore", 0, 0, tick, 0, parameter)
                  for parameter in sorted(self._active_locks[track])]
        self._active_locks[track].clear()
        return events

    def _step_locks(self, tick, track, source_step):
        events = self._restore_locks(tick, track)
        for parameter, value in source_step.locks:
            events.append(CapturedPlaybackEvent(tick // TICKS_PER_ROW, track,
                                                "lock", value, 0, tick, 0, parameter))
            self._active_locks[track][parameter] = value
        return events

    def set_fill(self, active: bool):
        if not isinstance(active, bool):
            raise ValueError("fill must be boolean")
        self.fill = active

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
        return tick, steps[index], pattern.phrase.source.steps[index]

    def _step_holds_gate(self, track):
        name = self.active[track]
        pattern = self.phrases[name]
        steps = pattern.synth_steps
        if not steps:
            return False
        current = (self._step[track] - 1) % len(steps)
        following = self._step[track] % len(steps)
        previous_source = pattern.phrase.source.steps[current]
        next_step = steps[following]
        if previous_source.ratchets:
            return False
        return bool(previous_source.flags & 2 or next_step.time == 1 or
                    (next_step.time == 0 and next_step.flags & 0xF8))

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
            times.extend(at for at, _, _ in steps.values())
            times.extend(hit.tick for hits in self._hits for hit in hits)
            times.extend(at for offs in self._note_offs for at in offs.values())
            if not times or min(times) > tick:
                break
            now = min(times)
            if now % TICKS_PER_ROW == 0:
                due, self.pending = pop_due(self.pending, now // TICKS_PER_ROW)
                for launch in due:
                    track = launch.track
                    events.extend(self._release(now, track))
                    events.extend(self._restore_locks(now, track))
                    self._hits[track] = []
                    self.active[track] = launch.phrase
                    self.started[track] = launch.at_row
                    self._track_transpose[track] = launch.transpose
                    self._step[track] = 0
            for track, offs in enumerate(self._note_offs):
                expired = sorted(note for note, at in offs.items() if at <= now)
                for note in expired:
                    if note in self.voices[track]:
                        events.append(self._event(now, track, "note_off", note))
                        self.voices[track].remove(note)
                    del offs[note]
            for track, name in enumerate(self.active):
                if name is None:
                    continue
                at, step, source_step = self._next_step(track)
                retained = set()
                if at == now:
                    self._step[track] += 1
                    condition = source_step.fill_condition
                    skipped = (condition == 1 and not self.fill) or (condition == 2 and self.fill)
                    if skipped:
                        events.extend(self._restore_locks(now, track))
                        self._hits[track] = []
                        if track < 3:
                            events.extend(self._release(now, track))
                    else:
                        events.extend(self._step_locks(now, track, source_step))
                        self._hits[track] = step_hits(step, track, at)
                        if track < 3 and step.time == 1:
                            deadline = now + (64 * self.gates[track] // 128) + 32
                            for note in self.voices[track]:
                                self._note_offs[track][note] = deadline
                        elif track < 3 and (step.time != 0 or not step.notes):
                            events.extend(self._release(now, track))
                        elif track < 3 and step.time == 0:
                            keep_mask = (source_step.flags >> 3) & 0x0F
                            retained = set()
                            for index, note in enumerate(step.notes):
                                if keep_mask & (1 << index) and note in self.voices[track]:
                                    retained.add(note)
                            for note in sorted(self.voices[track] - retained):
                                events.append(self._event(now, track, "note_off", note))
                                self.voices[track].discard(note)
                                self._note_offs[track].pop(note, None)
                            if retained:
                                if self._step_holds_gate(track):
                                    for note in retained:
                                        self._note_offs[track].pop(note, None)
                                else:
                                    base_gate = 64 * self.gates[track] // 128
                                    for note in retained:
                                        self._note_offs[track][note] = now + max(1, base_gate)
                due_hits = [hit for hit in self._hits[track] if hit.tick == now]
                self._hits[track] = [hit for hit in self._hits[track] if hit.tick > now]
                for hit in due_hits:
                    note = hit.note + (self._track_transpose[track] if not hit.drum else 0)
                    if not hit.drum:
                        step_index = next((i for i, candidate in enumerate(step.notes)
                                           if candidate == hit.note), 0)
                        if hit.hit_index == 0:
                            ratchets = max((1 + ((step.ratchets >> (2 * i)) & 3)
                                            for i in range(len(step.notes))), default=1)
                        else:
                            ratchets = hit.ratchets
                        gate = (64 // ratchets * self.gates[track]) // 128
                        if note in retained:
                            base_gate = 64 * self.gates[track] // 128
                            self._note_offs[track][note] = now + max(1, base_gate)
                            continue
                        if note in self.voices[track] and note not in retained:
                            events.append(self._event(now, track, "note_off", note))
                        self.voices[track].add(note)
                        if self._step_holds_gate(track):
                            self._note_offs[track].pop(note, None)
                        else:
                            self._note_offs[track][note] = now + max(1, gate)
                    events.append(self._event(now, track,
                                              "drum_hit" if hit.drum else "note_on",
                                              note, hit.velocity, hit.level))
        self.next_tick = tick + 1
        self.next_row = tick // TICKS_PER_ROW + 1
        return sorted(events, key=lambda e: (e.tick, e.kind != "note_off", e.track))

    def stop(self) -> list[CapturedPlaybackEvent]:
        """Release at the first unconsumed tick and cancel all future work."""
        events = []
        for track in range(4):
            events.extend(self._release(self.next_tick, track))
            events.extend(self._restore_locks(self.next_tick, track))
        self.active = [None] * 4
        self._track_transpose = [0] * 4
        self._hits = [[] for _ in range(4)]
        self.pending = ()
        return events
