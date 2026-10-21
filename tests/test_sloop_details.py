import unittest
from tracker.sloop_protocol import SynthStep, DrumStep
from tracker.sloop_details import synth_note_details, drum_lane_details
from tracker.sloop_capture import import_synth_pattern

class SloopDetailsTests(unittest.TestCase):
    def test_per_note_dynamics(self):
        s=SynthStep(0,0,(60,64,67),0,0,100,0b111001,0b100100)
        self.assertEqual(synth_note_details(s),((60,1,1),(64,2,2),(67,3,3)))
    def test_drum_per_lane_dynamics(self):
        s=DrumStep(0,0b101,0b11001,0b100100)
        self.assertEqual(drum_lane_details(s),((0,1,1),(2,3,3)))
    def test_reserved_fill_is_normal(self):
        s=SynthStep(0,0,(60,),0,0,100,0,0)
        imported=import_synth_pattern((s,),fills=(3,)+(0,)*63)
        self.assertEqual(imported.phrase.source.steps[0].fill,"normal")

if __name__ == "__main__":
    unittest.main()
