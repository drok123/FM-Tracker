import unittest
from tracker.launch import LaunchRequest, ScheduledLaunch, quantize_row, schedule_launch, queue_launch, pop_due

class LaunchTests(unittest.TestCase):
    def test_bar_quantization(self):
        self.assertEqual(quantize_row(17, "bar"), 32)
        self.assertEqual(quantize_row(16, "bar"), 16)
    def test_beat_and_phrase(self):
        self.assertEqual(quantize_row(5, "beat"), 8)
        self.assertEqual(quantize_row(17, "phrase", phrase_rows=12), 24)
    def test_independent_queue(self):
        pending = ()
        pending = queue_launch(pending, ScheduledLaunch(0, "A", 16))
        pending = queue_launch(pending, ScheduledLaunch(1, "B", 16))
        pending = queue_launch(pending, ScheduledLaunch(0, "C", 32))
        self.assertEqual([(x.track,x.phrase) for x in pending], [(1,"B"),(0,"C")])
    def test_due(self):
        due, future = pop_due((ScheduledLaunch(0,"A",16),ScheduledLaunch(1,None,32)),16)
        self.assertEqual(len(due),1)
        self.assertEqual(len(future),1)
    def test_request(self):
        self.assertEqual(schedule_launch(LaunchRequest(2,"B",19,"beat")).at_row,20)
    def test_invalid(self):
        with self.assertRaises(ValueError):
            quantize_row(-1,"bar")

if __name__ == "__main__":
    unittest.main()
