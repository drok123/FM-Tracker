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
        self.assertEqual([(h.note,h.velocity) for h in hits],
                         [(60,42),(64,72),(64,72)])
    def test_accent_and_drum_levels_use_sloop_velocity_mapping(self):
        synth = SynthStep(0,0,(60,64),0,1,80,0b01,0)
        self.assertEqual([h.velocity for h in
                          preview_hits(import_synth_pattern((synth,)),0)], [42,127])
        drums = DrumStep(0,0b111,0b111000,0)
        self.assertEqual([h.velocity for h in
                          preview_hits(import_drum_pattern((drums,)),3)], [100,72,127])
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
    def test_imported_nudges_are_used_by_default(self):
        step = SynthStep(0,0,(60,),0,0,90,0,0)
        pattern = import_synth_pattern((step,), nudges=(12,)+(0,)*63)
        self.assertEqual(preview_hits(pattern,0)[0].tick,12)
        self.assertEqual(preview_hits(pattern,0,nudges=(0,)*64)[0].tick,0)
    def test_drum_microtiming_and_dynamics(self):
        pattern = import_drum_pattern((DrumStep(0,4,2 << 4,2 << 4),),
                                      nudges=(-8,)+(0,)*63)
        self.assertEqual([(h.tick,h.note,h.level) for h in preview_hits(pattern,3)],
                         [(-8,2,2),(13,2,2),(34,2,2)])
    def test_invalid_nudges_rejected_at_capture(self):
        for nudge in (-33,32,1.5):
            with self.subTest(nudge=nudge):
                with self.assertRaises(ValueError):
                    import_synth_pattern((SynthStep(0,0,(60,),0,0,90,0,0),),
                                         nudges=(nudge,)+(0,)*63)
                with self.assertRaises(ValueError):
                    import_drum_pattern((DrumStep(0,1,0,0),),
                                        nudges=(nudge,)+(0,)*63)
    def test_reject_wrong_track(self):
        step = SynthStep(0,0,(60,),0,0,90,0,0)
        with self.assertRaises(ValueError):
            preview_hits(import_synth_pattern((step,)),2)

if __name__ == "__main__":
    unittest.main()
