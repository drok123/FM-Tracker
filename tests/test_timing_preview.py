import unittest
from tracker.sloop_protocol import SynthStep, DrumStep
from tracker.sloop_capture import import_synth_pattern, import_drum_pattern
from tracker.timing_preview import preview_hits

class TimingPreviewTests(unittest.TestCase):
    def test_chord_independent_ratchets(self):
        step = SynthStep(0,0,(60,64),0,0,100,0b1001,0b0100)
        hits = preview_hits(import_synth_pattern((step,)),0)
        self.assertEqual([(h.tick,h.note,h.level) for h in hits],
                         [(0,60,1),(0,64,2),(32,64,2)])
    def test_drum_ratchets(self):
        step = DrumStep(0,5,0,0b010000)
        hits = preview_hits(import_drum_pattern((step,)),3)
        self.assertEqual([(h.tick,h.note) for h in hits],
                         [(0,0),(0,2),(32,2)])
    def test_negative_nudge(self):
        step = SynthStep(1,0,(72,),0,0,90,0,0)
        hits = preview_hits(import_synth_pattern((step,)),1,
                            nudges=(-16,)+(0,)*63)
        self.assertEqual(hits[0].tick,-16)
    def test_repeat(self):
        step = SynthStep(0,0,(60,),0,0,90,0,0)
        hits = preview_hits(import_synth_pattern((step,)),0,rows=3)
        self.assertEqual([h.tick for h in hits],[0,64,128])
    def test_reject_wrong_track(self):
        step = SynthStep(0,0,(60,),0,0,90,0,0)
        with self.assertRaises(ValueError):
            preview_hits(import_synth_pattern((step,)),2)

if __name__ == "__main__":
    unittest.main()
