import unittest
from tracker.fast_track import SourceStep, SourcePattern, capture
from tracker.bridge import render_capture

class BridgeTests(unittest.TestCase):
    def test_chord_and_drum_ratchets(self):
        p = capture(SourcePattern((SourceStep(notes=(60,64,67), ratchet=2,
            drum_hits=((0,110,4),)),)))
        events = render_capture(p)
        self.assertEqual(len(events), 10)
        self.assertEqual([e.subtick for e in events if e.kind == "drum_hit"], [0,16,32,48])
        self.assertEqual([e.note_or_lane for e in events if e.kind == "note_on" and e.subtick == 0], [60,64,67])
    def test_nudge(self):
        p = capture(SourcePattern((SourceStep(notes=(60,), nudge=3),)))
        self.assertEqual(render_capture(p)[0].subtick, 3)
    def test_empty(self):
        p = capture(SourcePattern((SourceStep(),)))
        self.assertEqual(render_capture(p), [])

if __name__ == "__main__":
    unittest.main()
