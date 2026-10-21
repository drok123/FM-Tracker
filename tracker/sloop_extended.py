"""Additional read-only SLOOP protocol parsers (locks and fill conditions)."""
from dataclasses import dataclass
from .sloop_protocol import unpack_frame, pack7_decode, ProtocolError

@dataclass(frozen=True)
class ParameterLock:
    step: int
    parameter: int
    value: int

def parse_lock_get(frame: bytes) -> tuple[int, tuple[ParameterLock, ...]]:
    command, payload = unpack_frame(frame)
    if command != 37 or len(payload) < 2:
        raise ProtocolError("not LOCK_GET")
    track, count = payload[:2]
    if track >= 4 or count > 24 or len(payload) != 2 + 4 * count:
        raise ProtocolError("invalid lock count or length")
    locks = []
    for i in range(count):
        step, parameter, lo, hi = payload[2 + 4*i:6 + 4*i]
        if step >= 64:
            raise ProtocolError("invalid lock step")
        locks.append(ParameterLock(step, parameter, (lo | (hi << 7)) - 8192))
    return track, tuple(locks)

def parse_fill_get(frame: bytes) -> tuple[int, tuple[int, ...]]:
    command, payload = unpack_frame(frame)
    if command != 41 or len(payload) < 2 or payload[0] >= 4:
        raise ProtocolError("not FILL_GET")
    raw = pack7_decode(payload[1:])
    if len(raw) != 16:
        raise ProtocolError("invalid packed fill data")
    return payload[0], tuple((raw[i//4] >> (2*(i%4))) & 3 for i in range(64))
