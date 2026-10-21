import unittest
from tracker.sloop_capture import import_synth_pattern, import_drum_pattern
from tracker.sloop_protocol import SynthStep, DrumStep

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

if __name__ == "__main__":
    unittest.main()
