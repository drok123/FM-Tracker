# Captured pattern performance bridge

`CapturedPerformance` plays immutable `ImportedPattern` data as abstract events
on four independent tracks: synth 0-2 and drum lanes on track 3. It shares
`step_hits` with the offline timing preview; chords, each note/lane's packed
level and ratchet count, synth velocity and captured step nudges survive playback.
Import drum microtiming with `import_drum_pattern(steps, nudges=...)`.

## Time and event contract

- `advance_ticks(tick)` consumes through an absolute integer tick, inclusive,
  with 64 ticks per row. Skipped calls process all intervening events. Repeating
  the same endpoint emits nothing; moving backwards raises `ValueError`.
- `advance(row)` remains available and consumes through `row * 64`, inclusive.
  It does not consume the rest of that row: call `advance_ticks(row * 64 + 63)`
  to hear all its fine events before the following boundary.
- Events retain `row`, `track`, `kind`, `value`, `velocity` and add `tick` and
  `level`. `row` is the actual event tick divided by 64, rounded down.
  `level` is the raw 2-bit dynamics code, not a MIDI velocity. Synth velocity
  remains the captured base velocity; drum velocity remains zero. An eventual
  backend must apply upstream accent/default-velocity and level scaling and map
  drum lane IDs to instruments. These events are not directly MIDI messages.
- A note retrigger releases that pitch before its new note-on. A new NOTE or
  REST releases the previous chord at its nudged time; TIE sustains it.
  Same-tick note-offs precede note-ons across tracks.
- New steps replace remaining ratchets from the previous step. This matters when
  the next step fires early. `preview_hits` is an offline expansion and retains
  all potential hits, including those a live step transition would cancel.
- Queued launches stay on absolute row boundaries, with the last request winning
  per track. A launch first releases the old chord and cancels its pending hits,
  then starts the new phrase. A silent launch cancels playback on that track.
  A first step nudged early is clamped to the launch tick, with its ratchets
  relative to that clamped start. Later steps, including loop starts, can be early.
  An outgoing phrase's early step may legitimately sound before a queued boundary.
- `stop()` releases notes at the first unconsumed tick and cancels delayed hits,
  active phrases and queued launches. Repeated stops emit nothing.

Example (host only):

```python
player = CapturedPerformance({'A': captured_synth_pattern})
player.queue(ScheduledLaunch(0, 'A', 0))
events = player.advance_ticks(127)  # through two rows, before boundary 128
releases = player.stop()          # note-offs at tick 128
```

## Verification limits

This is an ideal integer-grid host reference, not accurate SLOOP firmware
playback. It sustains notes until explicit step/retrigger/launch/stop releases;
upstream instrument gate lengths are not captured. Swing, track divisions,
slides/legato/continuation flags, fill conditions, locks, recording, strum,
voice limits and audio-block rounding remain unimplemented. Three-way ratchets
use the preview's floor division (ticks 0, 21, 42), not upstream block thresholds.
No audio, sampling, recording or hardware behavior is verified by these tests.

The source projection remains read-only and the existing firmware clock and
audio engine were not modified. See [audit and upstream inspection](AUDIT.md).
