import unittest
from tracker.engine import Cell, Command, compile_pattern

class EngineTests(unittest.TestCase):
    def test_polyrhythm(self):
        events = compile_pattern([[Cell(60), Cell()], [Cell(36), Cell(), Cell()]], rows=6)
        notes = [(e.tick, e.track) for e in events if e.kind == "note_on"]
        self.assertEqual(notes, [(0, 0), (0, 1), (12, 0), (18, 1), (24, 0)])
    def test_retrigger(self):
        events = compile_pattern([[Cell(60, commands=(Command("R", 2),))]], rows=1)
        self.assertEqual([e.tick for e in events], [0, 2, 4])
    def test_probability_zero(self):
        self.assertEqual(compile_pattern([[Cell(60, commands=(Command("C", 0),))]]), [])
    def test_probability_full(self):
        self.assertEqual(len(compile_pattern([[Cell(60, commands=(Command("C", 100),))]], rows=8)), 8)
    def test_unsupported_command(self):
        with self.assertRaises(ValueError):
            compile_pattern([[Cell(60, commands=(Command("Z", 2),))]], rows=1)
    def test_volume_event_before_note(self):
        events = compile_pattern([[Cell(60, volume=90)]], rows=1)
        self.assertEqual([(e.kind, e.value) for e in events], [("volume", 90), ("note_on", 60)])

if __name__ == "__main__":
    unittest.main()
