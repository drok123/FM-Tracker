# FM-Tracker primary UI prototype

FM-Tracker is now the default startup application in the overlay. SLOOP's
native drivers, instruments, audio, event recorder, live patterns and project
storage remain underneath it. The [architecture audit](TRACKER_FIRST_AUDIT.md)
documents the source boundaries and measured hardware constraints.

The previous installed tracker-as-an-add-on build is preserved separately for
rollback. This new primary-interface candidate has not been installed or
hardware-tested. The previous screen's documentation is retained in
`docs/archive/TRACKER_ADDON_SCREEN.md`.

## First loop

Power on into STEP KEYS. Tap the white keys to place/remove steps on the
selected track, then press PLAY. No scene, capture, or phrase load is required.
SEQ switches instantly to NOTE KEYS: while stopped and disarmed, a musical key
plays its native sound, enters the mapped note at the cursor, and advances one
row. On drums it enters that key's native lane/hit. Press PLAY to hear the loop.

The editor changes the actual native `trk[]` steps that `seq_tick` plays. It
does not maintain a second pattern or automatically overwrite phrase-bank
slots. The existing working-project autosave preserves live patterns when
quiet, using its existing timing and storage rules; edits are not synchronously
written to flash on every key press. Use the SLOOP fallback for explicit project
save/load and advanced settings.

## Controls

| Control | Connected behavior |
| --- | --- |
| SEQ | Toggle STEP KEYS / NOTE KEYS; pending step gestures are canceled |
| White keys in STEP | Select the corresponding step on press; toggle it on release. An empty synth trigger uses the last entered pitch, initially C4. Black keys have no step action |
| Hold a white step key + knobs | Edit the selected held step; releasing it after a knob edit does not remove it. With several held keys, knobs target the most recently selected row |
| Keys in NOTE | Existing native audition. Stopped/disarmed: insert a single note/hit, advance one row, wrap at track length. Playing: audition; REC uses native event recording |
| ALGORITHM | Select track 1..4, including during playback; disabled while recording/count-in/free take is armed/active |
| PRESETS | Browse native instrument sounds across engines; on drums, select the kit. Sound changes retain pattern data. Disabled during armed/active recording/free take |
| SELECT | Move row within the selected track's actual length |
| GLO held + SELECT | Tempo, using native BPM bounds |
| OCT- / OCT+ | STEP: previous/next 16-step page, bounded by track length. NOTE: native keyboard octave -3..+3 |
| KNOB 1 | Synth: first chord note's pitch 0..127. Drum track: select lane 1..16 |
| KNOB 2 | Synth: row base velocity 1..127. Drum track: ghost/soft/normal/hard dynamics of selected lane |
| KNOB 3 | Ratchets x1..x4 for first synth chord note or selected drum lane |
| KNOB 4 | Native row microtiming -32..31 in 1/64-step units |
| EDIT / ARP | Native one-level undo / redo while stopped/disarmed; a held-step gesture is one undo session |
| PLAY | Existing loop transport start/stop, also from the help screen |
| REC | Switch to NOTE KEYS and invoke the existing live event recorder; also works from help. Existing count-in/free-take/quantization settings apply |
| HOME tap | Toggle on-device control help |
| HOME hold (~0.7 seconds) | Return to SLOOP's normal interface. Sound, running transport, note ownership and patterns are retained |

From SLOOP: stop/disarm, hold HOME for its menu, SELECT the SEQ section,
PRESETS to FM-TRACKER, OCT+ to reopen it. Tracker temporarily selects native
loop playback so an enabled song order cannot require scenes; the fallback's
arranger enable setting is restored when exiting. `FELUCCA_TRACKER_PRIMARY=0`
selects SLOOP startup at compile time while retaining the tracker menu item.
The build helper accepts that environment flag. `FELUCCA_TRACKER=0` removes
the tracker overlay as before.

## Screen and real data

The 240 x 240 screen shows all four physical tracks and eight rows at once.
The selected column expands to show note/hit and effective velocity. T1..T3
are general instrument parts, not assumed FM-only tracks; DR is the actual
drum part. The top line names the selected native engine and the real BPM.
Rows are numbered 1..64 in the interface (indices 0..63 internally). Each
track's own playhead is underlined; rows past its native length are blank.

The selected-row detail shows `N` chord-note count or `D` drum lane, `R`
ratchet count, `U` numeric microtiming, then six real indicators:
accent `A`, slide `S`, fill condition `F`, parameter lock `L`, first-note
continuation `C`, legato `G`; a dot means absent. Synth velocity is effective
velocity: accent and per-note dynamics can mask changes to the row's base
velocity. Existing chords are represented by their first note in the compact
table; the detail's note count makes that limitation visible.

All keys/buttons retain the saved backlight settings, including HIGH and ALL
KEYS if configured. Lit white keys in STEP mode also show existing triggers
for the current page/lane and the playhead; NOTE mode keeps sounding-note LEDs.

## Prototype boundaries

Direct programming/knob edits and undo require stopped/disarmed transport.
During playback, use NOTE for audition or REC for native recording. Note
programming is one note per key press, not chord collection; entering a new
synth note replaces that row's chord. Pitch/velocity/ratchet knob edits preserve
other chord voices, flags, fill and locks. Step toggling removes/adds that synth
trigger, or only the selected drum lane. Undo restores native steps/microtiming.

Live step toggling, chord expansion/editing beyond the first note, per-row
instrument IDs, per-step gate (native gate is per track), phrase/chain/song
editing, lock/fill entry, sample capture and richer undo are not implemented
in this primary screen. Existing FM and sample engines are available through
sound browsing; no new sampling engine or incoming audio path is claimed.
Advanced synthesis, recording setup, project controls and settings stay
accessible in the SLOOP fallback. User sample uploads and existing MIDI/editor
protocols remain compatible.

## Verification

The host test drives the real audio keyboard path and calibrated UI, tests
actual live sequence/recording data and native undo, and bounds-checks every
LCD transfer. It covers default application startup, white/black key mapping,
held-step editing, note advance, release across mode changes, track/page bounds,
recording guards, queue overflow, stale events, scene-free playback, fallback
and re-entry. Address/undefined-behavior sanitizer coverage and stock/tracker
sequencer/UI regressions are retained in CI. Build/package verification and
exact artifacts are recorded in `build-manifest.json`; hardware validation is
a separate remaining step.
