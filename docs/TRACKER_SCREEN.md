# Traditional tracker screen, first slice

This is a separate, opt-in screen in the pinned SLOOP overlay. SLOOP remains
the startup mode. Entering or leaving the screen does not load a phrase, start
transport, change sounds, or write flash. No device installation is performed
by the build or tests.

## Hardware and source inspection

The implementation targets SLOOP commit
`b77bf55e3bf804665b8f5dffb5955bd8443311f0`. The complete source change, including
`firmware/src/ui_tracker.c` and `tests/tracker_ui_test.c`, is distributed in
`patches/sloop-fm1-2.8-tracker.patch`.

- `firmware/src/lcd.c`: ST7789-class **240 x 240** SPI display, RGB565,
  DMA from RAM, synchronized before reusing a buffer.
- `gfx.c`: `cv_begin`, `cv_text`, `cv_blit`; existing `FONT_S` is Terminus
  8 x 16. The canvas holds at most 240 x 124 pixels, not a full framebuffer.
  The new screen uses separate 18/20/24-pixel strips and eight visible rows.
- `panel.c`: every control goes through the calibrated `panel.btn`,
  `panel.enc`, and `panel.dir` mapping. Default matrix button IDs are HOME=8,
  SEQ=11, PLAY=12, REC=13, OCT-=0, OCT+=1. Default encoder IDs are
  SELECT=0, ALGORITHM=1, PRESETS=6, KNOB 1..4=2..5.
- `ui_input.c` owns panel events, but `seq.c:layer_now` independently reads
  held buttons in audio processing. Tracker mode bypasses those keyboard
  layers so EDIT + a key cannot erase a live pattern behind this screen.
  Key ownership and release still use the existing keyboard engine.
- `fm_tracker_bank.c` already stores four native slots per physical track.
  Each record contains the 64 native synth/drum steps, microtiming, fill bits,
  24 locks, length, division, swing, and gate. Chains already load these
  records through `tracker_phrase_transition` before SLOOP's `seq_tick`.
  The screen edits these very records; it owns only cursor/display state.

## Controls

To enter: hold **HOME** (about 0.7 seconds), turn **SELECT** to the **SEQ**
menu section, turn **PRESETS** to **TRACKER MODE**, then tap **OCT+**.
The item says `STOP / DISARM FIRST` while transport or recording is active.
Stop and disarm using normal SLOOP controls before opening the screen.

| Control in tracker mode | Connected behavior |
| --- | --- |
| HOME tap or hold | Exit to SLOOP's normal TRACKS screen; no phrase load or transport change |
| ALGORITHM | Select physical SLOOP track 1..4 |
| PRESETS | Select that track's native phrase slot 1..4; browsing does not load it |
| SELECT | Select row, numbered 0..length-1, with eight-row paging |
| KNOB 3 | Select existing synth chord voice 1..4, or drum lane 1..16 |
| SEQ tap | While stopped/disarmed, capture the live track into the selected slot; replaces that RAM slot |
| KNOB 1 | While stopped/disarmed, change selected stored note 0..127; on an empty/rest/tie row with voice 1 selected, create C4 (60). Drum track: right enables the selected lane's hit, left disables it |
| KNOB 2 | While stopped/disarmed, change stored synth row base velocity 1..127. Drum track: step selected hit's dynamics through ghost, soft, normal, hard |
| KNOB 4 | While stopped/disarmed, change stored row microtiming -32..31, in native 1/64-step units |
| OCT+ tap | While stopped/disarmed, load the selected bank slot into its live track using the existing phrase transition; other tracks and the stored phrase remain unchanged |
| PLAY | Normal SLOOP transport request, including arranger validation; does not implicitly load a slot |
| Keyboard and incoming MIDI | Existing live sound/keyboard/MIDI paths; no tracker note entry from keys |
| REC, OCT-, other function buttons | No tracker edit action; exit to SLOOP for recording, layers, sound editing, saving, and tempo control |

Capture/edit/load are disabled during playback, pending transport requests,
armed/live recording, free takes, and count-in. Guards are checked again with
interrupts masked before mutations. A slot must exist before editing: an
empty slot says `EMPTY: SEQ CAPTURES LIVE`. Capture a live pattern first,
edit the bank, explicitly LOAD, then PLAY. Bank edits do not audition or change
the currently sounding/live sequence. Live recording and audio scheduling
remain SLOOP's responsibility. Navigation remains available during playback.

## What the columns mean

- **ROW**: native step index in the selected bank slot, not a second clock or
  an automatically followed playhead. The bright row is the edit cursor.
- **NOTE**: selected chord voice's actual MIDI note; `===` is a native tie,
  `---` is rest/absent voice. For drums it is `HIT`/`---` for the selected lane.
  KNOB 3 exposes all four existing chord notes without flattening the chord.
- **VEL**: effective selected note/hit's velocity, using SLOOP's existing
  level law and its default base 96. Synth accent forces base 127; per-note
  dynamics still apply. KNOB 2 edits the *row's base velocity*, so accent or
  dynamics may mask a change to that base. All other chord voices share it.
- **INS**: `T1`..`T3` refer to the track's current live sound; `D1`..`D16`
  identify drum lanes in the live kit. The native phrase has **no per-row
  instrument/preset ID**. This is a read-only reference, not an instrument
  selection or a placeholder instrument command. Sound parameters are not
  stored in a phrase and are not overwritten by LOAD.
- **FX**: eight compact indicators, `ASrMFLCG`:
  accent `A`, slide `S`, ratchet count `2`..`4`, nonzero microtiming `M`,
  fill condition `F`, parameter lock present `L`, selected note continuation
  `C`, and legato `G`; `.` means absent. The selected row's numeric
  microtiming appears below the table. Flags, all chord notes/dynamics/ratchets,
  drum lanes, locks, and fill bits survive capture and unrelated edits.

## Connected versus unavailable

The menu, navigation, capture, bounded note/drum/velocity/microtiming edits,
explicit native phrase load, transport, and row rendering are implemented.
The native chain/quantized-launch APIs remain connected to SLOOP's existing
audio engine, but **this screen does not configure or launch chains**. PLAY
plays the loaded live pattern through SLOOP, not an implicitly selected slot.
The arranger can still supersede live patterns when enabled, as in SLOOP.

Per-row instrument changes, arbitrary tracker FX command entry, tie/rest
entry, chord expansion/deletion, lock/fill/ratchet editing, tracker undo,
chain/song editing, and phrase-bank persistence are **unavailable**, not
working-looking buttons. No new bank serialization or project format is added.
Slots and unsaved bank edits are volatile. After LOAD, the normal SLOOP project
save flow can save the live pattern; it does not save the independent bank.

## Validation and rollback

`tracker_ui_test.c` drives the actual calibrated panel path, renders through
the bounds-checked 240 x 240 host framebuffer, and runs `mix_block` between UI
frames. It verifies menu entry/exit, no implicit load, empty-slot behavior,
track/slot/row/voice bounds, chord preservation, capture/load, synth and drum
editing, recording/playback guards, and held-button layer isolation. The same
test and the native phrase playback test run under address/undefined-behavior
sanitizers. Existing stock/tracker `seq2_test` and complete UI regressions,
including 20,000 random frames, cover normal SLOOP behavior.

The target build uses the existing JieLi pi32v2 clang 4.0.1 toolchain and the
hash-checked AC79NN SDK V1.2.1 (2023-12-13), with `FELUCCA_SLICE=0` as in the
installed build. See `build-manifest.json` for artifacts, memory usage,
package CRC/identity checks and device-validation status. A host pass or
successful target compilation does not establish hardware audio behavior.

The previous installed package is preserved separately, with SHA-256
`ad6f9de8fda132fe211c334fc2ac9bd4d5b10943d65f9e84648840b71720d34c`.
Its manifest and overlay are archived alongside it. The user confirmed that
build boots into SLOOP and works; detailed audio/recovery behavior has not
been independently measured. The new tracker-screen package is **not flashed**.
