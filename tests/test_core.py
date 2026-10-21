import unittest
from tracker.core import Step, schedule

class TrackerTests(unittest.TestCase):
    def test_independent_track_lengths(self):
        events = schedule([[Step(60), Step()], [Step(36), Step(), Step()]], rows=6)
        self.assertEqual([(e.tick, e.track) for e in events],
                         [(0,0),(0,1),(12,0),(18,1),(24,0)])
    def test_empty_track(self):
        self.assertEqual(schedule([[]]), [])
    def test_invalid_timing(self):
        with self.assertRaises(ValueError):
            schedule([[Step(60)]], ticks_per_row=0)

if __name__ == "__main__":
    unittest.main()
