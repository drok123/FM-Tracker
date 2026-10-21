# Fast Track: SLOOP input, tracker editing

## Goal
Keep SLOOP's tactile step/live input, then capture its musical data into
a tracker phrase for more detailed editing. Preserve source patterns,
including chords, drum lanes, velocity, ratchets, microtiming, ties,
slides, fill conditions, and parameter locks.

## Prototype implementation
`tracker/fast_track.py` provides an immutable host-side intermediate
representation and a non-destructive row-command overlay. A recapture
updates source note data while keeping extra tracker commands by row index.

**Important limitations:** This is not connected to SLOOP firmware or
its actual serialization format. The existing simple tracker compiler
currently emits only the first note of a chord and does not schedule
drum hits, locks, nudges, ties or slides. Those values are preserved in
the source model for later integration; they are not yet played.
If a pattern's row structure changes, index-based overlay matching may
attach commands to the wrong notes. A future adapter needs stable step
identities or an explicit reconciliation UI.

## Planned firmware integration
1. Identify SLOOP's actual pattern structures and recording hooks.
2. Capture SLOOP pattern snapshots without mutating source memory.
3. Add Fast Track UI to transfer, view, and edit phrases.
4. Use one playback owner per track; no simultaneous duplicate schedulers.
5. Support explicit unlink/commit with undo, plus project persistence.
6. Compare audio/MIDI timing and verify resource budgets on hardware.

No hardware firmware changes or flashable binaries are included.
