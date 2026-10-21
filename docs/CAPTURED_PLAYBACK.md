# Captured pattern performance bridge

`ImportedPattern.phrase.source.steps` is the canonical editable source model;
`tracker_rows` is a display/edit projection that only shows the first synth note.
The canonical row also retains all four notes, time, raw flags, base velocity,
packed per-note levels/ratchets, fill condition, parameter locks, nudge, track and
source index. Drum rows retain all 16-bit lane masks, packed 32-bit level/ratchet
fields and source index. The parallel parsed step tuple remains available for
exact protocol round-trips. `import_synth_pattern` accepts parsed lock and fill
replies; `import_drum_pattern` accepts microtiming offsets.

`CapturedPerformance` and the offline `preview_hits` share `step_hits` so chord,
per-note and lane ratchets, timing, dynamics and resolved SLOOP velocities agree.
Use `advance_ticks(absolute_tick)` for fine timing (64 ticks per host row) or
`advance(row)` for compatibility. Launches are row-quantized. Same-tick note-offs
precede new note-ons, and outgoing ratchets are cancelled at phrase or step
transitions. Early phrase steps are clamped to the launch boundary; early steps
inside a running phrase may fire in the preceding row.

The playback reference supports configurable synth gates (0..128), explicit
TIE/REST steps, matching-note continuation flags, fill-only/no-fill conditions,
parameter-lock events and lock restoration at steps/transitions/stops. Event
velocity uses SLOOP's `lvl_vel` mapping: normal levels use the step velocity
(or 96, or 127 under accent); ghost/soft/hard map to 42/72/127. Drum level 0
uses 100. Drum event values remain lane IDs; the downstream engine must map
those lanes to its instrument voices.

`CapturedChainPerformance` binds the four independent `TrackChain`s to captured
playback. Each track has independent entries, durations, repeats and loop/stop
state. Live requests can use row/beat/bar/phrase quantization, replace a pending
request, stop a track, restart its chain, transpose synth phrases and leave other
tracks running. A live launch matching a chain entry resumes from that entry;
a phrase outside the chain pauses it until restart.

`firmware/tracker_chain.[ch]` is a bounded, allocation-free C chain/launch state
module. Its caller passes absolute rows from SLOOP's existing transport callback;
it never makes or advances a clock. It emits phrase-change records for an
upstream adapter to release voices and select pattern data. A strict-warning
host C test covers independent chains, repeats, loops, stop/restart and all four
quantization grids.

## Remaining integration limits

The C module is not linked into `isod89/sloop-fm1` and calls no SLOOP note,
parameter or audio APIs. No firmware-facing source was changed. Slides/glide,
voice-pool behavior, exact SLOOP block rounding and parameter value restoration
against live engine parameters are not reproduced by the host model. Parameter
lock restore events identify the parameter and tell a backend to restore its
base value; the model does not own that base. Tracker editing commands are not
a second complete SLOOP step editor. Do not treat abstract events or the C
selection state as flashed firmware behavior.

The module and host tests add no evidence about audio deadlines, the JieLi AC79
target build, storage compatibility or a physical FM-1. The upstream transport,
audio ISR, synth/drum engines, recording, MIDI and project format remain in the
separately inspected SLOOP checkout. See [AUDIT.md](AUDIT.md).
