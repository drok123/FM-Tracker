import unittest
from tracker.engine import Command
from tracker.fast_track import SourceStep, SourcePattern, capture, set_commands, refresh_source, tracker_view

class FastTrackTests(unittest.TestCase):
    def test_capture_preserves_source_details(self):
        step = SourceStep(notes=(60, 64, 67), ratchet=3, nudge=-7,
                          locks=((4, 90),), slide=True)
        phrase = capture(SourcePattern((step,)))
        self.assertEqual(phrase.source.steps[0], step)
        self.assertEqual(tracker_view(phrase)[0].note, 60)
    def test_commands_survive_recapture(self):
        original = capture(SourcePattern((SourceStep(notes=(60,)),)))
        edited = set_commands(original, 0, (Command("C", 50),))
        refreshed = refresh_source(edited, SourcePattern((SourceStep(notes=(62,)),)))
        self.assertEqual(tracker_view(refreshed)[0].note, 62)
        self.assertEqual(tracker_view(refreshed)[0].commands, (Command("C", 50),))
    def test_original_is_immutable(self):
        original = capture(SourcePattern((SourceStep(notes=(60,)),)))
        edited = set_commands(original, 0, (Command("R", 2),))
        self.assertEqual(tracker_view(original)[0].commands, ())
        self.assertEqual(edited.revision, 1)
    def test_drum_data_preserved(self):
        step = SourceStep(drum_hits=((0, 100, 2), (5, 60, 1)))
        self.assertEqual(capture(SourcePattern((step,))).source.steps[0].drum_hits, step.drum_hits)

if __name__ == "__main__":
    unittest.main()
