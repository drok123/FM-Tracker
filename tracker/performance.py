"""Host reference performance transport: launch, switch and release voices.

Single-note tracker projection only. SLOOP chords, drum voices and tied notes
require an upstream-aware adapter before firmware integration.
"""
from dataclasses import dataclass
from .engine import Cell
from .launch import ScheduledLaunch, queue_launch, pop_due

@dataclass(frozen=True)
class PlaybackEvent:
    row: int
    track: int
    kind: str
    note: int

class Performance:
    def __init__(self, phrases: dict[str, tuple[Cell, ...]], tracks: int = 4):
        if tracks <= 0:
            raise ValueError("tracks must be positive")
        self.phrases = phrases
        self.active: list[str | None] = [None] * tracks
        self.started: list[int] = [0] * tracks
        self.sounding: list[int | None] = [None] * tracks
        self.pending: tuple[ScheduledLaunch, ...] = ()
        self.next_row = 0

    def queue(self, launch: ScheduledLaunch) -> None:
        if not 0 <= launch.track < len(self.active):
            raise ValueError("invalid track")
        if launch.at_row < self.next_row:
            raise ValueError("launch is in the past")
        if launch.phrase is not None and launch.phrase not in self.phrases:
            raise ValueError("unknown phrase")
        self.pending = queue_launch(self.pending, launch)

    def advance(self, row: int) -> list[PlaybackEvent]:
        """Process every row since last call; safe when transport skips rows."""
        if row < self.next_row - 1:
            raise ValueError("cannot rewind without reset")
        result: list[PlaybackEvent] = []
        while self.next_row <= row:
            now = self.next_row
            due, self.pending = pop_due(self.pending, now)
            for launch in due:
                t = launch.track
                if self.sounding[t] is not None:
                    result.append(PlaybackEvent(now, t, "note_off", self.sounding[t]))
                    self.sounding[t] = None
                self.active[t] = launch.phrase
                self.started[t] = now
            for track, name in enumerate(self.active):
                if name is None:
                    continue
                cells = self.phrases[name]
                if not cells:
                    continue
                cell = cells[(now - self.started[track]) % len(cells)]
                if cell.note is None:
                    continue
                if not 0 <= cell.note <= 127:
                    raise ValueError("invalid note")
                if self.sounding[track] is not None:
                    result.append(PlaybackEvent(now, track, "note_off", self.sounding[track]))
                result.append(PlaybackEvent(now, track, "note_on", cell.note))
                self.sounding[track] = cell.note
            self.next_row += 1
        return result

    def stop(self) -> list[PlaybackEvent]:
        result = [PlaybackEvent(self.next_row, track, "note_off", note)
                  for track, note in enumerate(self.sounding) if note is not None]
        self.active = [None] * len(self.active)
        self.sounding = [None] * len(self.sounding)
        self.pending = ()
        return result
