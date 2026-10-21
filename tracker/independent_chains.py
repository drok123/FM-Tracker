"""Independent per-track phrase chains, compiled on the host.

A chain entry has its own duration and repetition count. Track chains advance
independently; shorter chains may loop while longer chains continue.
"""
from dataclasses import dataclass
from .engine import Cell, TrackerEvent, compile_pattern
from .captured_performance import CapturedPerformance, CapturedPlaybackEvent
from .launch import LaunchRequest, ScheduledLaunch, schedule_launch
from .timing_preview import TICKS_PER_ROW

@dataclass(frozen=True)
class PhraseRef:
    name: str | None
    rows: int
    repeats: int = 1
    transpose: int = 0

@dataclass(frozen=True)
class TrackChain:
    entries: tuple[PhraseRef, ...]
    loop: bool = False

@dataclass(frozen=True)
class ChainSong:
    phrases: dict[str, tuple[Cell, ...]]
    tracks: tuple[TrackChain, ...]
    total_rows: int
    ticks_per_row: int = 6

def compile_chains(song: ChainSong) -> list[TrackerEvent]:
    if song.total_rows < 0 or song.ticks_per_row <= 0:
        raise ValueError("invalid song timing")
    output: list[TrackerEvent] = []
    for track_id, chain in enumerate(song.tracks):
        timeline: list[tuple[PhraseRef, int]] = []
        for entry in chain.entries:
            if entry.rows <= 0 or entry.repeats <= 0:
                raise ValueError("entry rows and repeats must be positive")
            if entry.name is not None and entry.name not in song.phrases:
                raise ValueError("missing phrase: " + entry.name)
            for _ in range(entry.repeats):
                timeline.append((entry, entry.rows))
        if not timeline:
            continue
        chain_length = sum(rows for _, rows in timeline)
        cursor = 0
        while cursor < song.total_rows:
            for entry, duration in timeline:
                if cursor >= song.total_rows:
                    break
                span = min(duration, song.total_rows - cursor)
                if entry.name is not None and song.phrases[entry.name]:
                    shifted = []
                    for cell in song.phrases[entry.name]:
                        note = None if cell.note is None else cell.note + entry.transpose
                        if note is not None and not 0 <= note <= 127:
                            raise ValueError("transposition out of MIDI range")
                        shifted.append(Cell(note, cell.instrument, cell.volume, cell.commands))
                    events = compile_pattern([shifted], rows=span, ticks_per_row=song.ticks_per_row)
                    output.extend(TrackerEvent(cursor * song.ticks_per_row + event.tick,
                                               track_id, event.kind, event.value, event.instrument)
                                  for event in events)
                cursor += span
            if not chain.loop:
                break
            if chain_length == 0:
                break
    return sorted(output, key=lambda e: (e.tick, e.track, 0 if e.kind == "volume" else 1))


class CapturedChainPerformance:
    """Run four independent captured-pattern chains on the shared fine clock.

    Direct launches replace the pending launch per track. A manual phrase that
    is in its chain resumes there; any other phrase or stop pauses that chain
    until ``restart_track``. Chain boundaries reset the selected phrase at the
    boundary, even when other tracks are midway through their own entries.
    """
    def __init__(self, phrases, chains: tuple[TrackChain, ...], *,
                 rows_per_beat=4, beats_per_bar=4, phrase_rows=16):
        if len(chains) != 4:
            raise ValueError("captured SLOOP playback requires four track chains")
        self.player = CapturedPerformance(phrases)
        self.chains = chains
        self.rows_per_beat = rows_per_beat
        self.beats_per_bar = beats_per_bar
        self.phrase_rows = phrase_rows
        self._cursor = [[0, 0, False, None] for _ in range(4)]
        self._manual: list[ScheduledLaunch | None] = [None] * 4
        self._start_rows: list[int | None] = [None] * 4
        for track, chain in enumerate(chains):
            self._validate_chain(track, chain)

    def _validate_chain(self, track, chain):
        for entry in chain.entries:
            if entry.rows <= 0 or entry.repeats <= 0:
                raise ValueError("entry rows and repeats must be positive")
            if entry.name is not None and entry.name not in self.player.phrases:
                raise ValueError("missing phrase: " + entry.name)
            if entry.name is not None:
                phrase = self.player.phrases[entry.name]
                if track == 3 and (not phrase.drum_steps or phrase.synth_steps):
                    raise ValueError("drum chain requires drum phrases")
                if track < 3 and (not phrase.synth_steps or phrase.drum_steps or
                                  any(step.track != track for step in phrase.synth_steps)):
                    raise ValueError("synth chain phrase belongs to another track")

    def _queue_entry(self, track, row):
        index, repeat, running, _ = self._cursor[track]
        chain = self.chains[track]
        if not running:
            self._cursor[track][3] = None
            return
        entry = chain.entries[index]
        self.player.queue(ScheduledLaunch(track, entry.name, row, entry.transpose))
        self._cursor[track][3] = row + entry.rows

    def start_track(self, track: int, row: int):
        if not 0 <= track < 4 or row * TICKS_PER_ROW < self.player.next_tick:
            raise ValueError("invalid chain start")
        chain = self.chains[track]
        self._manual[track] = None
        self._start_rows[track] = row
        if not chain.entries:
            self._cursor[track] = [0, 0, False, None]
            self.player.queue(ScheduledLaunch(track, None, row))
            return
        self._cursor[track] = [0, 0, True, None]
        self._queue_entry(track, row)

    def restart_track(self, track: int, row: int):
        self.start_track(track, row)

    def stop_track(self, track: int, row: int):
        self.queue_launch(track, None, row, quantum="row")

    def queue_launch(self, track: int, phrase: str | None, requested_row: int,
                     *, quantum="row", transpose=0):
        if not 0 <= track < 4:
            raise ValueError("invalid track")
        launch = schedule_launch(LaunchRequest(track, phrase, requested_row, quantum),
                                 rows_per_beat=self.rows_per_beat,
                                 beats_per_bar=self.beats_per_bar,
                                 phrase_rows=self.phrase_rows)
        launch = ScheduledLaunch(launch.track, launch.phrase, launch.at_row, transpose)
        self.player.queue(launch)
        self._manual[track] = launch

    def _manual_applied(self, track, launch):
        chain = self.chains[track]
        match = next((i for i, entry in enumerate(chain.entries)
                      if entry.name == launch.phrase and entry.transpose == launch.transpose), None)
        if match is None:
            self._cursor[track] = [0, 0, False, None]
        else:
            self._cursor[track] = [match, 0, True,
                                   launch.at_row + chain.entries[match].rows]

    def advance_ticks(self, tick: int) -> list[CapturedPlaybackEvent]:
        if not isinstance(tick, int) or tick < self.player.next_tick - 1:
            raise ValueError("cannot rewind")
        events = []
        while True:
            boundaries = [cursor[3] for cursor in self._cursor if cursor[3] is not None]
            boundaries.extend(launch.at_row for launch in self._manual if launch is not None)
            boundaries.extend(row for row in self._start_rows if row is not None)
            if not boundaries or min(boundaries) * TICKS_PER_ROW > tick:
                break
            row = min(boundaries)
            boundary_tick = row * TICKS_PER_ROW
            if boundary_tick > self.player.next_tick:
                events.extend(self.player.advance_ticks(boundary_tick - 1))
            for track in range(4):
                manual = self._manual[track]
                if manual is not None and manual.at_row == row:
                    self._manual[track] = None
                    self._start_rows[track] = None
                    # A chain boundary may have queued this same row before
                    # the manual launch arrived; the live request wins there.
                    self.player.queue(manual)
                    self._manual_applied(track, manual)
                    continue
                if self._start_rows[track] == row:
                    self._start_rows[track] = None
                    self._queue_entry(track, row)
                    continue
                index, repeat, running, boundary = self._cursor[track]
                if boundary != row or not running:
                    continue
                chain = self.chains[track]
                entry = chain.entries[index]
                if repeat + 1 < entry.repeats:
                    self._cursor[track][1] += 1
                else:
                    self._cursor[track][1] = 0
                    index += 1
                    if index >= len(chain.entries):
                        if chain.loop:
                            index = 0
                        else:
                            self._cursor[track] = [0, 0, False, None]
                            self.player.queue(ScheduledLaunch(track, None, row))
                            continue
                    self._cursor[track][0] = index
                self._queue_entry(track, row)
            events.extend(self.player.advance_ticks(boundary_tick))
        if tick >= self.player.next_tick:
            events.extend(self.player.advance_ticks(tick))
        return events
