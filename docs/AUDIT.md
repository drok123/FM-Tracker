# FM-Tracker architecture audit - 2026-10-21

## Baseline and scope

Audited `dev/tracker-core` at `c15c06f`. Existing suite:
`python -m unittest discover -s tests -v`, Python 3.11.9 on Windows,
**62 passed** before changes. This repository contains a Python reference model,
not firmware sources, an FM-1 build target or a hardware adapter.

## Findings

1. **High: separate playback implementations lost captured data.**
   `captured_performance.py` originally emitted row-only chord notes and plain
   drum triggers; `timing_preview.py` separately expanded levels and ratchets.
   Captured synth nudges were ignored by default preview, while drum capture
   could not accept microtiming. Resolved for the host model by shared step
   expansion, imported nudge validation and fine-tick performance events.

2. **High: timing-dependent transitions needed cancellation and voice ownership.**
   Simply forwarding preview hits would let outgoing ratchets sound after a
   launch or after an early next step. The integrated player owns pending hits
   per track/step, cancels them on switches/stops/new steps, and releases synth
   pitches before retriggers and phrase changes. Regression tests cover late
   outgoing ratchets, early incoming steps, tied destinations and same pitches.

3. **High, open: instrument gates and engine semantics are absent.**
   The reference still sustains notes until explicit releases. It cannot reproduce
   upstream gate, slide/legato, fill, parameter lock, swing, division, strum or
   voice-pool behavior. Raw level/base velocity are preserved, not converted to
   final engine velocity. Drum events remain lane IDs, not synth note numbers.
   Never dispatch them directly to a device without an instrument adapter.

4. **High, open: chains and tracker editing use a lossy projection.**
   `fast_track.capture` puts only the first chord note into `Cell`;
   `compile_chains` and `compile_arrangement` consume those cells and return
   `TrackerEvent` without releases. `CapturedPerformance` uses raw captured steps,
   preserving chords but not applying editable `extras` commands. The separate
   `Performance`, `render_capture` and timing models also differ in timing units
   and release semantics. A future captured-chain adapter should schedule phrase
   references into this player rather than flatten captures into single notes.
   Do not claim complete tracker-command/chaining integration from this change.

5. **Medium, open: transport/protocol boundaries need explicit contracts.**
   Tracker compilation defaults to 6 ticks/row; captured preview uses 64. Neither
   maps to upstream sample/BPM units or captures complete track settings. Protocol
   tests use constructed fixtures, not hardware captures or upstream C comparison.
   Add versioned capture metadata and C/reference differential fixtures before a
   production port. Imported patterns are read-only snapshots, not device I/O.

6. **High, open: preservation of firmware features is unverified.**
   There is no embedded integration/build here. Synthesis, sample playback,
   recording, USB/MIDI, storage, step editing and audio deadlines must remain
   owned by upstream until tested integration exists. Host unit tests establish
   event semantics only. No hardware was flashed or accessed.

## Upstream inspected before implementation

Inspected a separate read-only checkout of
[isod89/sloop-fm1](https://github.com/isod89/sloop-fm1) pinned at
`b77bf55e3bf804665b8f5dffb5955bd8443311f0` (SLOOP 2.8).
Earlier project notes described 2.6; those are not the inspected revision.

- `firmware/src/core.h`: packed four-note synth steps, 16 drum lanes, per-note
  2-bit dynamics/ratchets, microtiming -32..31, and 44.1 kHz transport definitions.
- `firmware/src/seq.c`: `seq_step`, `seq_release`, `seq_ratchets`, `micro_units`,
  `seq_tick`, and `events_block`. Sequencing runs in the audio ISR once per
  control block. All tracks read the existing shared clock via `trk_grid`;
  `events_block` advances `clk_pos`/`clk_beat`, including external clock handling.
  Ratchets belong to the playing step; synth retriggers issue note-off first.
  Ties/gates/continuation flags have richer semantics than the reference model.
- `firmware/src/fx.c`: `mix_block` invokes `events_block` before rendering.
- `firmware/src/audio.c`: DMA/I2S interrupt rendering in control-sized blocks.
- `firmware/src/drums.c`: lane-to-note mapping and level-to-velocity conversion.
- `LICENSE`, `LICENSING.md`: GPL-3.0-only code; separate assets and third-party
  licenses. No upstream source or assets were imported by this change.

No changes were made to upstream transport, audio, engines or recording. Any
future bounded C adapter should run in the existing event domain, use upstream
note APIs and clock, and preserve its queues/input/recording paths. First add
host C comparisons, then build firmware, measure event density, SRAM and audio
block deadlines. Hardware verification remains a separate required milestone.

## Validation after changes

**80 Python tests pass** (62 original plus 18 regressions), including shared
preview/playback dynamics, x1-x4 chord ratchets, drum microtiming, early/late
steps, loop timing, release ordering, cancellation, independent tracks, last
launch wins, stop, rewind rejection, and chunked-versus-single-call equivalence.
`git diff --check` also passes. Upstream C tests and embedded builds were not run;
this change adds no hardware-facing code and cannot verify firmware behavior.
