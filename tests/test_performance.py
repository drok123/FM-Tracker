import unittest
from tracker.engine import Cell
from tracker.launch import ScheduledLaunch
from tracker.performance import Performance

class PerformanceTests(unittest.TestCase):
    def test_switch_releases_before_note_on(self):
        p = Performance({"A":(Cell(60),),"B":(Cell(62),)},1)
        p.queue(ScheduledLaunch(0,"A",0))
        p.advance(0)
        p.queue(ScheduledLaunch(0,"B",4))
        events = p.advance(4)
        at_four = [(e.kind,e.note) for e in events if e.row==4]
        self.assertEqual(at_four,[("note_off",60),("note_on",62)])
    def test_stop_releases(self):
        p = Performance({"A":(Cell(60),)},1)
        p.queue(ScheduledLaunch(0,"A",0))
        p.advance(0)
        self.assertEqual([(e.kind,e.note) for e in p.stop()],[("note_off",60)])
    def test_silent_launch(self):
        p = Performance({"A":(Cell(60),)},1)
        p.queue(ScheduledLaunch(0,"A",0))
        p.advance(0)
        p.queue(ScheduledLaunch(0,None,1))
        self.assertEqual([(e.kind,e.note) for e in p.advance(1)],[("note_off",60)])
    def test_skipped_rows(self):
        p = Performance({"A":(Cell(60),Cell(61))},1)
        p.queue(ScheduledLaunch(0,"A",0))
        self.assertEqual([(e.row,e.note) for e in p.advance(2) if e.kind=="note_on"],
                         [(0,60),(1,61),(2,60)])
    def test_queue_rejects_past(self):
        p = Performance({},1)
        p.advance(0)
        with self.assertRaises(ValueError):
            p.queue(ScheduledLaunch(0,None,0))

if __name__ == "__main__":
    unittest.main()
