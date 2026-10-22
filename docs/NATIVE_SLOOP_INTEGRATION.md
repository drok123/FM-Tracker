# Native phrase bank and SLOOP sequencing overlay

The implementation is carried as `patches/sloop-fm1-2.8-tracker.patch` against
SLOOP commit `b77bf55e3bf804665b8f5dffb5955bd8443311f0`. The patch leaves SLOOP's
four project scenes as whole-project snapshots and adds a separate bank of four
phrase slots for each of the four SLOOP tracks. A 16-entry chain can reuse those
four per-track slots in any order. Existing scenes are copied into matching
phrase slots at startup when the scene is valid; later phrase edits do not alter
the source scene. When SLOOP applies a whole-project scene during playback, any
currently active tracker phrases are reapplied afterward, so scene snapshots
remain intact while the independent phrase layer continues.

Each phrase copies SLOOP's native 64-step union (`step_t` or `dstep_t`), all
per-step microtiming, packed fill conditions, all 24 parameter locks, and the
pattern length, division, swing, and gate. The normal SLOOP synth step retains
all four notes, flags, dynamics, and per-note ratchets. The native drum step
retains all 16 lanes and their dynamics and ratchets. Slots can also be captured
from the current live track with `fm_tracker_phrase_capture`, or imported from
one track of a project scene with `fm_tracker_phrase_import_scene`.

The phrase bank occupies 13,184 bytes for its 16 fixed-size phrase records,
plus a four-byte validity bitmap. This is the host/compiler size from the
declared SLOOP C types; it is not a target memory-budget result. Writes mask the
audio interrupt while a slot is copied. Phrase capture and import are control
side operations and must not be called from the audio callback.

SLOOP remains the only transport and audio scheduler. In `events_block`, the
overlay converts `clk_beat` and `clk_pos` to a 16th-note row, advances each
independent chain, and applies transitions immediately before the existing
`seq_tick` loop. A phrase transition copies only that track's pattern fields,
sets that phrase's step-zero origin, and leaves voice handling to SLOOP's
`seq_step`, `drum_step`, ratchet, fill, and lock code. The bank remains unmodified
when chain transposition is applied to the live track copy.

SLOOP owns note lifetime. The transition restores locks still owned by the old
phrase before loading the new lock table. It retains current note ownership so
native TIE, continuation, slide, and gate behavior can resolve at the new first
step. A REST or ordinary note then releases or replaces notes through SLOOP's
existing logic. An explicit track stop releases that track and suppresses only
its sequencer; keyboard and MIDI input and the other tracks remain on SLOOP's
existing paths. A transport stop resets chain runtime, and the next transport
start restores normal stock-track sequencing until a chain is started again.

`FELUCCA_TRACKER` defaults to `1` in the FM-Tracker overlay. Setting it to `0`
omits the phrase storage and chain hooks and preserves SLOOP's stock sequencer
layout and index calculations. The CI job builds and runs SLOOP's existing
`seq2_test.c` in both modes, then builds `tracker_phrase_test.c` through the
actual `mix_block` → `events_block` → `seq_tick` path, including AddressSanitizer
and UndefinedBehaviorSanitizer runs.

The overlay exposes native storage and chain APIs, but this milestone does not
add screen controls for editing the bank or building chains, nor save the new
bank to flash. A JieLi AC79 target build has succeeded, and its `FM-1_900`
package passes the local SLOOP installer preflight for the two-stage Felucca
update format and package CRCs. The installer patch adds `--fm-tracker` to pin
that product identity and `--verify-only` to perform checks without MIDI access.
The stock-device handshake and actual FM-1 playback remain unverified. Do not
flash until the device identity and recovery path have been confirmed.
