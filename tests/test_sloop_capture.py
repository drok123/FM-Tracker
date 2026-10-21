import unittest
from tracker.sloop_capture import import_synth_pattern, import_drum_pattern
from tracker.sloop_protocol import SynthStep, DrumStep
from tracker.sloop_extended import ParameterLock

class CaptureTests(unittest.TestCase):
    def test_chord_and_tie(self):
        raw = (SynthStep(0,0,(60,64,67),0,0,100,0,0),
               SynthStep(0,1,(),1,0,100,0,0))
        result = import_synth_pattern(raw)
        self.assertEqual(result.phrase.source.steps[0].notes,(60,64,67))
        self.assertTrue(result.phrase.source.steps[1].tie)
        self.assertEqual(result.synth_steps,raw)
    def test_reject_gaps(self):
        with self.assertRaises(ValueError):
            import_synth_pattern((SynthStep(0,1,(60,),0,0,100,0,0),))
    def test_drum_lanes(self):
        result = import_drum_pattern((DrumStep(0,5,0,0),))
        self.assertEqual([x[0] for x in result.phrase.source.steps[0].drum_hits],[0,2])
        self.assertEqual(result.drum_steps[0].on,5)
    def test_lossless_canonical_synth_metadata_and_projection(self):
        source_step = SynthStep(2, 0, (60, 64, 67, 71), 0, 0xB7,
                                109, 0xE4, 0x39)
        locks = (ParameterLock(0, 12, -8192), ParameterLock(0, 14, 8191))
        imported = import_synth_pattern((source_step,), nudges=(-17,) + (0,) * 63,
                                        fills=(1,) + (0,) * 63, locks=locks)
        canonical = imported.phrase.source.steps[0]
        self.assertEqual((canonical.notes, canonical.time, canonical.flags,
                          canonical.velocity, canonical.levels, canonical.ratchets,
                          canonical.nudge, canonical.fill_condition,
                          canonical.source_track, canonical.source_index),
                         (source_step.notes, source_step.time, source_step.flags,
                          source_step.velocity, source_step.levels, source_step.ratchets,
                          -17, 1, 2, 0))
        self.assertEqual(canonical.locks, ((12, -8192), (14, 8191)))
        self.assertEqual(imported.synth_steps, (source_step,))
        self.assertEqual(imported.phrase.tracker_rows[0].note, 60)
    def test_lossless_canonical_drum_packed_fields(self):
        source_step = DrumStep(0, 0xA501, 0xE4D3C2B1, 0x12345678)
        imported = import_drum_pattern((source_step,))
        canonical = imported.phrase.source.steps[0]
        self.assertEqual((canonical.drum_on, canonical.levels, canonical.ratchets,
                          canonical.source_index),
                         (source_step.on, source_step.levels, source_step.ratchets, 0))
        self.assertEqual(imported.drum_steps, (source_step,))

if __name__ == "__main__":
    unittest.main()
