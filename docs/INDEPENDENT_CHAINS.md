# Independent pattern chains

`compile_chains` remains a simple, single-note tracker-cell renderer for existing
callers. For captured SLOOP patterns, use `CapturedChainPerformance` from
`tracker.independent_chains`; it connects per-track chains to the lossless
captured playback path.

Each of the four SLOOP tracks owns a list of `PhraseRef(name, rows, repeats,
transpose)` entries and a loop flag. A phrase's own step length wraps while the
chain entry occupies its configured duration. Tracks advance independently;
short loops and long entries do not need aligned boundaries. A non-looping chain
queues a silent launch at its end. Repeats restart the phrase at the entry
boundary, and an early nudge in the new phrase is clamped to that boundary.

Use `queue_launch(track, phrase, requested_row, quantum=...)` for live launches.
The quantization grids are row, beat, bar and phrase. A later request replaces
the pending request for that track. Launching a phrase already in the chain
resumes that entry; launching a different phrase or `None` pauses the chain.
`restart_track(track, row)` restarts from its first entry. Other tracks continue.
Synth transpose is validated against MIDI range. Drum transposition is rejected.

This Python chain is a host reference. The bounded C selector in
`firmware/tracker_chain.[ch]` stores up to 16 entries per track and emits only
pattern-selection changes. The adapter that maps those changes into SLOOP voice
release, step data and the existing audio callback still needs implementation
inside the upstream firmware source tree.
