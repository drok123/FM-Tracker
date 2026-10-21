"""Read-only SLOOP editor SysEx adapter, based on upstream EDITOR_PROTOCOL.md.

Parses responses for TRACK_STEP (30), DRUM_STEP (33), MICRO_GET (39).
No USB I/O, no writes, no firmware flashing.
"""
from dataclasses import dataclass

HEADER = bytes((0xF0, 0x7D, 0x46, 0x4C))
TRACK_STEP = 30
DRUM_STEP = 33
MICRO_GET = 39

class ProtocolError(ValueError):
    pass

def unpack_frame(frame: bytes) -> tuple[int, bytes]:
    if len(frame) < 6 or frame[:4] != HEADER or frame[-1] != 0xF7:
        raise ProtocolError("invalid SLOOP SysEx framing")
    if any(b > 127 for b in frame[4:-1]):
        raise ProtocolError("invalid 7-bit SysEx data")
    return frame[4], frame[5:-1]

def pack7_decode(data: bytes) -> bytes:
    out = bytearray()
    offset = 0
    while offset < len(data):
        mask = data[offset]
        offset += 1
        chunk = data[offset:offset + 7]
        if not chunk:
            raise ProtocolError("pack7 missing data")
        for bit, value in enumerate(chunk):
            out.append(value | (((mask >> bit) & 1) << 7))
        offset += len(chunk)
    return bytes(out)

@dataclass(frozen=True)
class SynthStep:
    track: int
    index: int
    notes: tuple[int, ...]
    time: int
    flags: int
    velocity: int
    levels: int
    ratchets: int

def parse_track_step(frame: bytes) -> SynthStep:
    command, payload = unpack_frame(frame)
    if command != TRACK_STEP or len(payload) < 7:
        raise ProtocolError("not a TRACK_STEP reply")
    track, index, n = payload[:3]
    if track >= 4 or index >= 64 or n > 4:
        raise ProtocolError("invalid track, step or chord size")
    # Upstream TRACK_STEP response: track, index, n, notes[n], time, flags,
    # vel, [lvl, hi, rat]. 'hi' is the high portion of level bits.
    tail = payload[3 + n:]
    if len(tail) not in (3, 6):
        raise ProtocolError("invalid TRACK_STEP payload length")
    notes = tuple(payload[3:3 + n])
    time, flags, velocity = tail[:3]
    if time > 2:
        raise ProtocolError("invalid step time")
    lvl, hi, rat = tail[3:] if len(tail) == 6 else (0, 0, 0)
    return SynthStep(track, index, notes, time, flags, velocity,
                     lvl | (hi << 7), rat)

@dataclass(frozen=True)
class DrumStep:
    index: int
    on: int
    levels: int
    ratchets: int

def parse_drum_step(frame: bytes) -> DrumStep:
    command, payload = unpack_frame(frame)
    if command != DRUM_STEP or len(payload) != 14:
        raise ProtocolError("not a DRUM_STEP reply")
    index = payload[0]
    if index >= 64:
        raise ProtocolError("invalid drum step")
    def number(data):
        return sum(b << (7 * i) for i, b in enumerate(data))
    return DrumStep(index, number(payload[1:4]), number(payload[4:9]),
                    number(payload[9:14]))

def parse_micro_get(frame: bytes) -> tuple[int, tuple[int, ...]]:
    command, payload = unpack_frame(frame)
    if command != MICRO_GET or len(payload) != 65 or payload[0] >= 4:
        raise ProtocolError("not a MICRO_GET reply")
    nudges = tuple(int(b) - 64 for b in payload[1:])
    if any(n < -32 or n > 31 for n in nudges):
        raise ProtocolError("invalid nudge")
    return payload[0], nudges
