import unittest
from tracker.sloop_protocol import (
    HEADER, ProtocolError, unpack_frame, pack7_decode, parse_track_step,
    parse_drum_step, parse_micro_get,
)
def frame(command, payload):
    return HEADER + bytes((command,)) + bytes(payload) + bytes((0xF7,))

class SloopProtocolTests(unittest.TestCase):
    def test_chord_step(self):
        s = parse_track_step(frame(30, [1, 7, 3, 60, 64, 67, 0, 2, 100, 3, 0, 1]))
        self.assertEqual(s.notes, (60,64,67))
        self.assertEqual((s.track, s.index, s.velocity), (1,7,100))
    def test_drum_step(self):
        s = parse_drum_step(frame(33, [4, 1,0,0] + [0]*10))
        self.assertEqual((s.index, s.on), (4,1))
    def test_microtiming(self):
        track, nudges = parse_micro_get(frame(39, [2]+[64]*63+[95]))
        self.assertEqual((track, nudges[-1]), (2,31))
    def test_pack7(self):
        self.assertEqual(pack7_decode(bytes([1, 1, 2])), bytes([129,2]))
    def test_reject_corruption(self):
        with self.assertRaises(ProtocolError):
            unpack_frame(b"invalid")
    def test_reject_bad_track(self):
        with self.assertRaises(ProtocolError):
            parse_track_step(frame(30, [9,0,0,0,0,0]))

    def test_empty_legacy_step(self):
        s = parse_track_step(frame(30, [0, 0, 0, 2, 0, 0]))
        self.assertEqual(s.notes, ())

if __name__ == "__main__":
    unittest.main()
