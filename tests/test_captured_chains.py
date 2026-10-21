import unittest

from tracker.independent_chains import CapturedChainPerformance, PhraseRef, TrackChain
from tracker.launch import LaunchRequest
from tracker.sloop_capture import import_synth_pattern, import_drum_pattern
from tracker.sloop_protocol import SynthStep, DrumStep


class CapturedChainTests(unittest.TestCase):
    def setUp(self):
        self.phrases = {
            'A': import_synth_pattern((SynthStep(0, 0, (60,), 0, 0, 90, 0, 0),)),
            'B': import_synth_pattern((SynthStep(0, 0, (64,), 0, 0, 90, 0, 0),)),
            'C': import_synth_pattern((SynthStep(0, 0, (67,), 0, 0, 90, 0, 0),)),
            'D': import_synth_pattern((SynthStep(1, 0, (72,), 0, 0, 90, 0, 0),)),
            'H': import_drum_pattern((DrumStep(0, 1, 0, 0),)),
        }
        self.chains = (TrackChain((PhraseRef('A', 2, 2), PhraseRef('B', 1)), True),
                       TrackChain((PhraseRef('D', 3),), False),
                       TrackChain((), False),
                       TrackChain((PhraseRef('H', 2),), True))

    def player(self):
        return CapturedChainPerformance(self.phrases, self.chains)

    def test_independent_boundaries_repeats_loop_and_stop(self):
        player = self.player()
        for track in (0, 1, 3):
            player.start_track(track, 0)
        events = player.advance_ticks(6 * 64 + 10)
        by_track = {track: [(e.tick, e.kind, e.value) for e in events if e.track == track]
                    for track in range(4)}
        self.assertEqual(by_track[0], [
            (0, 'note_on', 60), (64, 'note_off', 60), (64, 'note_on', 60),
            (128, 'note_off', 60), (128, 'note_on', 60),
            (192, 'note_off', 60), (192, 'note_on', 60),
            (256, 'note_off', 60), (256, 'note_on', 64),
            (320, 'note_off', 64), (320, 'note_on', 60),
            (384, 'note_off', 60), (384, 'note_on', 60)])
        self.assertEqual([event for event in by_track[1] if event[0] == 192],
                         [(192, 'note_off', 72)])
        self.assertEqual(by_track[2], [])
        self.assertEqual([event[0] for event in by_track[3] if event[1] == 'drum_hit'],
                         [0, 64, 128, 192, 256, 320, 384])

    def test_live_launch_quantization_replacement_and_restart(self):
        player = self.player()
        player.start_track(0, 0)
        player.queue_launch(0, 'B', 1, quantum='bar', transpose=2)
        player.queue_launch(0, 'C', 2, quantum='bar', transpose=-1)
        events = player.advance_ticks(16 * 64)
        self.assertIn((16 * 64, 'note_on', 66),
                      [(e.tick, e.kind, e.value) for e in events])
        self.assertFalse(player._cursor[0][2])
        player.restart_track(0, 17)
        events = player.advance_ticks(17 * 64)
        self.assertIn((17 * 64, 'note_on', 60),
                      [(e.tick, e.kind, e.value) for e in events])

    def test_future_launch_does_not_drop_initial_chain_phrase(self):
        player = self.player()
        player.start_track(0, 0)
        player.queue_launch(0, 'C', 16)
        events = player.advance_ticks(16 * 64)
        notes = [(e.tick, e.value) for e in events if e.kind == 'note_on' and e.track == 0]
        self.assertIn((0, 60), notes)
        self.assertIn((16 * 64, 67), notes)

    def test_live_launch_on_chain_phrase_resumes_at_that_entry(self):
        player = self.player()
        player.start_track(0, 0)
        player.queue_launch(0, 'B', 1)
        events = player.advance_ticks(17 * 64)
        timeline = [(e.tick, e.kind, e.value) for e in events]
        self.assertIn((16 * 64, 'note_on', 64), timeline)
        self.assertIn((17 * 64, 'note_on', 60), timeline)
        self.assertTrue(player._cursor[0][2])

    def test_stop_one_track_leaves_others_running(self):
        player = self.player()
        player.start_track(0, 0)
        player.start_track(1, 0)
        player.start_track(3, 0)
        player.advance_ticks(0)
        player.stop_track(0, 1)
        events = player.advance_ticks(3 * 64)
        self.assertIn((64, 'note_off', 60), [(e.tick, e.kind, e.value) for e in events])
        self.assertIn((3 * 64, 'note_off', 72),
                      [(e.tick, e.kind, e.value) for e in events])
        self.assertTrue(player._cursor[3][2])

    def test_bad_chain_references_and_duration_rejected(self):
        with self.assertRaises(ValueError):
            CapturedChainPerformance(self.phrases,
                (TrackChain((PhraseRef('MISSING', 1),)),) + self.chains[1:])
        with self.assertRaises(ValueError):
            CapturedChainPerformance(self.phrases,
                (TrackChain((PhraseRef('A', 0),)),) + self.chains[1:])
        with self.assertRaises(ValueError):
            self.player().start_track(0, -1)

    def test_live_launch_wins_at_same_row_as_queued_chain_boundary(self):
        player = CapturedChainPerformance(
            self.phrases,
            (TrackChain((PhraseRef('A', 2), PhraseRef('B', 2)), True),) + self.chains[1:])
        player.start_track(0, 0)
        player.advance_ticks(64)
        player.queue_launch(0, 'C', 2)
        events = player.advance_ticks(3 * 64)
        at_row_two = [(e.kind, e.value) for e in events if e.tick == 2 * 64]
        self.assertEqual(at_row_two, [('note_off', 60), ('note_on', 67)])


if __name__ == '__main__':
    unittest.main()
