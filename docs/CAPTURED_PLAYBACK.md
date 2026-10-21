# Captured pattern performance bridge

`CapturedPerformance` accepts `ImportedPattern` objects, routes synth
patterns to tracks 0–2 and drum patterns to track 3, and applies queued
`ScheduledLaunch` changes at absolute transport rows. It emits note-on,
note-off, and drum-hit **abstract events**, not audio or MIDI output.

The first pass preserves chord note-ons, ties as sustained notes, rests as
releases, and releases all active notes before a phrase switch. Drum triggers
are per enabled lane. A stop releases synth voices.

**Not yet accurate SLOOP playback:** drum ratchets/levels, per-note synth
levels/ratchets, swing, microtiming, slides, fill conditions, locks, note
gates, and audio-block timing remain unimplemented. The source pattern
projection remains read-only; no firmware was changed. Never use this
host model as an ISR drop-in without an upstream scheduler audit.
