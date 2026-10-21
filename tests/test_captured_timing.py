import unittest

from tracker.captured_performance import CapturedPerformance
from tracker.launch import ScheduledLaunch
from tracker.sloop_capture import import_synth_pattern, import_drum_pattern
from tracker.sloop_protocol import SynthStep, DrumStep
from tracker.sloop_extended import ParameterLock
from tracker.timing_preview import preview_hits


def phrase(track=0, notes=(60, 64), ratchets=4, nudges=None):
    return import_synth_pattern((SynthStep(track, 0, notes, 0, 0, 91, 9, ratchets),),
                                nudges=nudges)


def timeline(events):
    return [(e.tick, e.track, e.kind, e.value, e.velocity, e.level) for e in events]


class CapturedTimingTests(unittest.TestCase):
    def start(self, pattern, track=0):
        player = CapturedPerformance({'A': pattern})
        player.queue(ScheduledLaunch(track, 'A', 0))
        return player

    def test_chord_ratchets_and_levels_match_preview(self):
        pattern = phrase()
        events = self.start(pattern).advance_ticks(63)
        self.assertEqual([(e.tick, e.track, e.value, e.level, e.velocity)
                          for e in events if e.kind == 'note_on'],
                         [(h.tick, h.track, h.note, h.level, h.velocity)
                          for h in preview_hits(pattern, 0)])
        self.assertEqual([(e.tick, e.kind, e.value) for e in events],
                         [(0, 'note_on', 60), (0, 'note_on', 64),
                          (32, 'note_off', 60), (32, 'note_off', 64),
                          (32, 'note_on', 64)])

    def test_drum_dynamics_ratchets_nudge_match_preview(self):
        pattern = import_drum_pattern((DrumStep(0, 5, 3 | (2 << 4), 2 << 4),),
                                      nudges=(8,) + (0,) * 63)
        events = self.start(pattern, 3).advance_ticks(63)
        self.assertEqual([(e.tick, e.track, e.value, e.level, e.velocity)
                          for e in events],
                         [(h.tick, h.track, h.note, h.level, h.velocity)
                          for h in preview_hits(pattern, 3)])
        self.assertTrue(all(e.kind == 'drum_hit' for e in events))

    def test_four_note_chord_with_all_ratchet_counts(self):
        pattern = import_synth_pattern((SynthStep(0, 0, (60, 64, 67, 71),
                                                  0, 0, 104, 228, 228),))
        events = self.start(pattern).advance_ticks(63)
        self.assertEqual([(e.tick, e.value, e.level, e.velocity)
                          for e in events if e.kind == 'note_on'],
                         [(h.tick, h.note, h.level, h.velocity)
                          for h in preview_hits(pattern, 0)])
        self.assertEqual(sum(e.kind == 'note_on' for e in events), 10)
        self.assertEqual(sum(e.kind == 'note_off' for e in events), 8)

    def test_negative_nudge_and_rest_release(self):
        pattern = import_synth_pattern((SynthStep(0, 0, (60,), 0, 0, 90, 0, 0),
                                        SynthStep(0, 1, (), 2, 0, 0, 0, 0)),
                                       nudges=(0, -16) + (0,) * 62)
        events = self.start(pattern).advance_ticks(63)
        self.assertEqual([(e.tick, e.kind) for e in events],
                         [(0, 'note_on'), (48, 'note_off')])

    def test_positive_nudge_delays_release_to_step(self):
        pattern = import_synth_pattern((SynthStep(0, 0, (60,), 0, 0, 90, 0, 0),
                                        SynthStep(0, 1, (), 2, 0, 0, 0, 0)),
                                       nudges=(0, 16) + (0,) * 62)
        player = self.start(pattern)
        self.assertEqual([(e.tick, e.kind) for e in player.advance_ticks(79)
                          if e.kind == 'note_off'], [(64, 'note_off')])

    def test_early_launch_step_clamped_but_loop_can_be_early(self):
        player = CapturedPerformance({'A': phrase(notes=(60,), ratchets=0,
                                                  nudges=(-16,) + (0,) * 63)})
        player.queue(ScheduledLaunch(0, 'A', 2))
        self.assertEqual(player.advance_ticks(127), [])
        self.assertEqual([(e.tick, e.kind) for e in player.advance_ticks(176)],
                         [(128, 'note_on'), (176, 'note_off'), (176, 'note_on')])

    def test_launch_cancels_outgoing_late_ratchets_and_releases_chord(self):
        player = CapturedPerformance({'A': phrase(ratchets=15,
                                                   nudges=(31,) + (0,) * 63),
                                      'B': phrase(notes=(67,), ratchets=0)})
        player.queue(ScheduledLaunch(0, 'A', 0))
        player.queue(ScheduledLaunch(1, None, 1))  # unrelated track stays independent
        player.advance_ticks(63)
        player.queue(ScheduledLaunch(0, 'B', 1))
        self.assertEqual([(e.tick, e.kind, e.value) for e in player.advance_ticks(94)],
                         [(64, 'note_off', 60), (64, 'note_off', 64),
                          (64, 'note_on', 67)])

    def test_early_step_cancels_previous_ratchets(self):
        pattern = import_synth_pattern((SynthStep(0, 0, (60,), 0, 0, 90, 0, 3),
                                        SynthStep(0, 1, (62,), 0, 0, 90, 0, 0)),
                                       nudges=(31, -32) + (0,) * 62)
        events = self.start(pattern).advance_ticks(63)
        self.assertEqual([(e.tick, e.kind, e.value) for e in events],
                         [(31, 'note_on', 60), (32, 'note_off', 60),
                          (32, 'note_on', 62)])

    def test_switch_to_tie_releases_old_voices(self):
        tie = import_synth_pattern((SynthStep(0, 0, (), 1, 0, 0, 0, 0),))
        player = CapturedPerformance({'A': phrase(), 'T': tie})
        player.queue(ScheduledLaunch(0, 'A', 0))
        player.advance_ticks(63)
        player.queue(ScheduledLaunch(0, 'T', 1))
        self.assertEqual([(e.kind, e.value) for e in player.advance_ticks(127)],
                         [('note_off', 64)])
        self.assertEqual(player.voices[0], set())

    def test_quantized_silent_launch_cancels_drum_ratchets(self):
        pattern = import_drum_pattern((DrumStep(0, 1, 3, 3),),
                                      nudges=(31,) + (0,) * 63)
        player = self.start(pattern, 3)
        player.advance_ticks(63)
        player.queue(ScheduledLaunch(3, None, 1))
        self.assertEqual(player.advance_ticks(150), [])

    def test_stop_cancels_delayed_first_hit_and_pending_launch(self):
        player = self.start(phrase(nudges=(31,) + (0,) * 63))
        player.advance_ticks(0)
        player.queue(ScheduledLaunch(0, 'A', 2))
        self.assertEqual(player.stop(), [])
        self.assertEqual(player.advance_ticks(200), [])
        self.assertEqual(player.stop(), [])

    def test_stop_releases_at_first_unconsumed_tick(self):
        player = self.start(phrase())
        player.advance_ticks(33)
        self.assertEqual([(e.tick, e.kind, e.value) for e in player.stop()],
                         [(34, 'note_off', 64)])
        self.assertEqual(player.advance_ticks(150), [])

    def test_independent_tracks_and_chunk_invariance(self):
        patterns = {'A': phrase(nudges=(8,) + (0,) * 63),
                    'B': import_synth_pattern((SynthStep(1, 0, (72,), 0, 0, 90, 0, 2),
                                               SynthStep(1, 1, (), 1, 0, 0, 0, 0)),
                                              nudges=(0, -16) + (0,) * 62)}
        def setup():
            player = CapturedPerformance(patterns)
            player.queue(ScheduledLaunch(0, 'A', 0))
            player.queue(ScheduledLaunch(1, 'B', 0))
            return player
        whole, chunked = setup(), setup()
        expected = timeline(whole.advance_ticks(300))
        actual = []
        for tick in range(301):
            actual.extend(timeline(chunked.advance_ticks(tick)))
            self.assertEqual(chunked.advance_ticks(tick), [])
        self.assertEqual(actual, expected)
        self.assertEqual(chunked.voices, whole.voices)
        self.assertEqual([e.value for e in whole.stop()], [64, 72])

    def test_reject_rewind_and_launch_in_consumed_tick(self):
        player = self.start(phrase())
        player.advance_ticks(65)
        with self.assertRaises(ValueError):
            player.advance_ticks(64)
        with self.assertRaises(ValueError):
            player.queue(ScheduledLaunch(0, 'A', 1))
        for tick in (-1, 1.5):
            with self.assertRaises(ValueError):
                player.advance_ticks(tick)

    def test_last_queue_wins_and_same_note_releases_before_restart(self):
        player = self.start(phrase(notes=(60,), ratchets=0))
        player.advance(0)
        player.queue(ScheduledLaunch(0, None, 1))
        player.queue(ScheduledLaunch(0, 'A', 1))
        self.assertEqual([(e.tick, e.kind) for e in player.advance(1)],
                         [(64, 'note_off'), (64, 'note_on')])

    def test_sloop_gate_percentage_and_tie_extension(self):
        pattern = import_synth_pattern((SynthStep(0, 0, (60,), 0, 0, 90, 0, 0),
                                        SynthStep(0, 1, (), 2, 0, 0, 0, 0)))
        gated = CapturedPerformance({'A': pattern}, gate=64)
        gated.queue(ScheduledLaunch(0, 'A', 0))
        events = gated.advance_ticks(127)
        self.assertIn((32, 'note_off'), [(e.tick, e.kind) for e in events])
        tied_pattern = import_synth_pattern((SynthStep(0, 0, (60,), 0, 0, 90, 0, 0),
                                             SynthStep(0, 1, (), 1, 0, 0, 0, 0),
                                             SynthStep(0, 2, (), 2, 0, 0, 0, 0)))
        tied = CapturedPerformance({'A': tied_pattern}, gate=64)
        tied.queue(ScheduledLaunch(0, 'A', 0))
        tied_events = tied.advance_ticks(128)
        self.assertEqual([(e.tick, e.kind) for e in tied_events if e.kind == 'note_off'],
                         [(128, 'note_off')])

    def test_fill_conditions_apply_on_step_and_preserve_toggle(self):
        fills = (1, 2, 0, 0) + (0,) * 60
        steps = tuple(SynthStep(0, i, (60 + i,), 0, 0, 90, 0, 0)
                      for i in range(4))
        pattern = import_synth_pattern(steps, fills=fills)
        player = CapturedPerformance({'A': pattern})
        player.queue(ScheduledLaunch(0, 'A', 0))
        player.set_fill(True)
        events = player.advance_ticks(3 * 64)
        self.assertEqual([(e.tick, e.value) for e in events if e.kind == 'note_on'],
                         [(0, 60), (128, 62), (192, 63)])
        no_fill = CapturedPerformance({'A': pattern})
        no_fill.queue(ScheduledLaunch(0, 'A', 0))
        events = no_fill.advance_ticks(3 * 64)
        self.assertEqual([(e.tick, e.value) for e in events if e.kind == 'note_on'],
                         [(64, 61), (128, 62), (192, 63)])

    def test_locks_apply_restore_on_step_switch_and_stop(self):
        a = import_synth_pattern((SynthStep(0, 0, (60,), 0, 0, 90, 0, 0),),
                                 locks=(ParameterLock(0, 5, -10),))
        b = import_synth_pattern((SynthStep(0, 0, (62,), 0, 0, 90, 0, 0),),
                                 locks=(ParameterLock(0, 5, 20),
                                        ParameterLock(0, 6, 30)))
        player = CapturedPerformance({'A': a, 'B': b})
        player.queue(ScheduledLaunch(0, 'A', 0))
        player.advance_ticks(0)
        player.queue(ScheduledLaunch(0, 'B', 1))
        events = player.advance_ticks(64)
        self.assertEqual([(e.kind, e.parameter, e.value) for e in events
                          if e.kind.startswith('lock')],
                         [('lock_restore', 5, 0), ('lock', 5, 20), ('lock', 6, 30)])
        self.assertEqual([(e.kind, e.parameter) for e in player.stop()
                          if e.kind == 'lock_restore'],
                         [('lock_restore', 5), ('lock_restore', 6)])

    def test_continuation_keeps_matching_voice_without_retrigger(self):
        pattern = import_synth_pattern((SynthStep(0, 0, (60,), 0, 0, 90, 0, 0),
                                        SynthStep(0, 1, (60,), 0, 8, 90, 0, 0)))
        player = CapturedPerformance({'A': pattern}, gate=32)
        player.queue(ScheduledLaunch(0, 'A', 0))
        events = player.advance_ticks(64)
        self.assertEqual([(e.tick, e.kind, e.value) for e in events],
                         [(0, 'note_on', 60)])
        self.assertEqual(player.voices[0], {60})
        chunked = CapturedPerformance({'A': pattern}, gate=32)
        chunked.queue(ScheduledLaunch(0, 'A', 0))
        chunked.advance_ticks(0)
        self.assertEqual(chunked.advance_ticks(64), [])


if __name__ == '__main__':
    unittest.main()
