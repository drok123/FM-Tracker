import unittest
from tracker.engine import Cell
from tracker.arrangement import Arrangement, ChainSlot, SongPosition, compile_arrangement

class ArrangementTests(unittest.TestCase):
    def test_phrase_reuse_and_independent_lengths(self):
        song = Arrangement(
            {"A": (Cell(60), Cell()), "B": (Cell(36), Cell(), Cell())},
            (SongPosition((ChainSlot("A"), ChainSlot("B")), rows=6),
             SongPosition((ChainSlot("B"), ChainSlot("A")), rows=6)))
        notes = [(e.tick,e.track,e.value) for e in compile_arrangement(song) if e.kind=="note_on"]
        self.assertEqual(notes, [(0,0,60),(0,1,36),(12,0,60),(18,1,36),(24,0,60),
                                 (36,0,36),(36,1,60),(48,1,60),(54,0,36),(60,1,60)])
    def test_mute_and_rest(self):
        song = Arrangement({"A":(Cell(60),)},
            (SongPosition((ChainSlot("A", muted=True),ChainSlot(None)),rows=2),))
        self.assertEqual(compile_arrangement(song), [])
    def test_transpose_preserves_original(self):
        phrase = (Cell(60),)
        song = Arrangement({"A":phrase},(SongPosition((ChainSlot("A", transpose=12),),rows=1),))
        self.assertEqual([e.value for e in compile_arrangement(song) if e.kind=="note_on"],[72])
        self.assertEqual(phrase[0].note,60)
    def test_missing_phrase(self):
        with self.assertRaises(ValueError):
            compile_arrangement(Arrangement({},(SongPosition((ChainSlot("X"),)),)))
    def test_track_count_consistency(self):
        song=Arrangement({"A":(Cell(60),)},(SongPosition((ChainSlot("A"),)),
            SongPosition((ChainSlot("A"),ChainSlot("A")))))
        with self.assertRaises(ValueError):
            compile_arrangement(song)

if __name__ == "__main__":
    unittest.main()
