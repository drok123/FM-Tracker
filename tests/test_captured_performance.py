import unittest
from tracker.sloop_capture import import_synth_pattern, import_drum_pattern
from tracker.sloop_protocol import SynthStep, DrumStep
from tracker.captured_performance import CapturedPerformance
from tracker.launch import ScheduledLaunch

def synth(track, index, notes, time=0):
    return SynthStep(track,index,notes,time,0,100,0,0)

class CapturedPerformanceTests(unittest.TestCase):
    def test_chord_tie_rest_and_switch(self):
        a=import_synth_pattern((synth(0,0,(60,64)),synth(0,1,(),1),
                                synth(0,2,(),2)))
        b=import_synth_pattern((synth(0,0,(67,)),))
        p=CapturedPerformance({"A":a,"B":b})
        p.queue(ScheduledLaunch(0,"A",0))
        ev=p.advance(2)
        self.assertEqual([(x.row,x.kind,x.value) for x in ev],
                         [(0,"note_on",60),(0,"note_on",64),
                          (2,"note_off",60),(2,"note_off",64)])
        p.queue(ScheduledLaunch(0,"B",3))
        self.assertEqual([(x.kind,x.value) for x in p.advance(3)],
                         [("note_on",67)])
        self.assertEqual([(x.kind,x.value) for x in p.stop()],
                         [("note_off",67)])
    def test_drum_lane_triggers(self):
        d=import_drum_pattern((DrumStep(0,5,0,0),))
        p=CapturedPerformance({"D":d})
        p.queue(ScheduledLaunch(3,"D",0))
        self.assertEqual([x.value for x in p.advance(0) if x.kind=="drum_hit"],[0,2])
    def test_reject_wrong_track(self):
        a=import_synth_pattern((synth(0,0,(60,)),))
        p=CapturedPerformance({"A":a})
        with self.assertRaises(ValueError):
            p.queue(ScheduledLaunch(1,"A",0))
    def test_launch_releases_before_new_chord(self):
        a=import_synth_pattern((synth(0,0,(60,)),))
        b=import_synth_pattern((synth(0,0,(62,)),))
        p=CapturedPerformance({"A":a,"B":b})
        p.queue(ScheduledLaunch(0,"A",0))
        p.advance(0)
        p.queue(ScheduledLaunch(0,"B",1))
        self.assertEqual([(e.kind,e.value) for e in p.advance(1)],
                         [("note_off",60),("note_on",62)])

if __name__ == "__main__":
    unittest.main()
