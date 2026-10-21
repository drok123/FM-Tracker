import unittest
from tracker.sloop_extended import parse_lock_get, parse_fill_get
from tracker.sloop_protocol import HEADER, ProtocolError

def frame(command, payload):
    return HEADER + bytes((command,)) + bytes(payload) + bytes((0xf7,))

class ExtendedTests(unittest.TestCase):
    def test_locks_signed(self):
        track, locks = parse_lock_get(frame(37, [1,2,0,12,0,64,7,5,127,63]))
        self.assertEqual(track, 1)
        self.assertEqual([(x.step,x.value) for x in locks], [(0,0),(7,-1)])
    def test_fill(self):
        raw = bytes([0b00100100] + [0]*15)
        # 16 zero-high-bit bytes -> 3 pack7 groups (7+7+2).
        packed = bytes([0]) + raw[:7] + bytes([0]) + raw[7:14] + bytes([0]) + raw[14:]
        track, fills = parse_fill_get(frame(41, bytes([2])+packed))
        self.assertEqual(track,2)
        self.assertEqual(fills[:4], (0,1,2,0))
    def test_reject_short_locks(self):
        with self.assertRaises(ProtocolError):
            parse_lock_get(frame(37, [0,1]))

if __name__ == "__main__":
    unittest.main()
