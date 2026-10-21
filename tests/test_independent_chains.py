import unittest
from tracker.engine import Cell
from tracker.independent_chains import PhraseRef, TrackChain, ChainSong, compile_chains

class IndependentChainsTests(unittest.TestCase):
    def test_independent_advancement(self):
        song = ChainSong(
            {"K": (Cell(36),), "B": (Cell(48),)},
            (TrackChain((PhraseRef("K", rows=2, repeats=2),), loop=True),
             TrackChain((PhraseRef("B", rows=4),), loop=False)), total_rows=8)
        notes = [(e.tick,e.track) for e in compile_chains(song) if e.kind == "note_on"]
        self.assertEqual([t for t,tr in notes if tr == 0], [0,6,12,18,24,30,36,42])
        self.assertEqual([t for t,tr in notes if tr == 1], [0,6,12,18])
    def test_silent_entry(self):
        song = ChainSong({"A":(Cell(60),)},(TrackChain((PhraseRef(None,2),PhraseRef("A",2))),),4)
        self.assertEqual([e.tick for e in compile_chains(song) if e.kind == "note_on"],[12,18])
    def test_transpose(self):
        song = ChainSong({"A":(Cell(60),)},(TrackChain((PhraseRef("A",1,transpose=12),)),),1)
        self.assertEqual([e.value for e in compile_chains(song) if e.kind == "note_on"],[72])
    def test_reject_bad_duration(self):
        song = ChainSong({},(TrackChain((PhraseRef(None,0),)),),4)
        with self.assertRaises(ValueError):
            compile_chains(song)
    def test_stop_without_loop(self):
        song = ChainSong({"A":(Cell(60),)},(TrackChain((PhraseRef("A",1),)),),4)
        self.assertEqual(len([e for e in compile_chains(song) if e.kind == "note_on"]),1)

if __name__ == "__main__":
    unittest.main()
