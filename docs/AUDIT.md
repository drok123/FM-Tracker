# FM-Tracker architecture audit - 2026-10-21

## Repository and baseline

Working branch `dev/tracker-core`, starting at `9736a50`. The first test run
before this development pass had 80 passing Python tests. The FM-Tracker
repository is primarily a Python reference project; the inspected SLOOP firmware
is a separate repository and is not a submodule or build target here.

## Changes in this pass

- Expanded canonical `SourceStep` to retain packed synth/drum data, all chord
  pitches, raw SLOOP time/flags, velocity, source indices, per-note/lane dynamics,
  fill condition, microtiming and parameter locks alongside the simple editor row.
- Added SLOOP level-to-velocity conversion to the shared preview/playback step
  expansion.
- Added captured playback of gate lengths, ties, RESTs, matching-note
  continuation, fill conditions, parameter-lock application/restoration,
  transpose, and safe track transitions. Slide/glide behavior stays represented
  by the preserved flags and is not simulated.
- Added `CapturedChainPerformance` to run independent captured pattern chains
  with durations, repeats, loop/stop, per-track live launches, quantization,
  restart and transposition.
- Added an allocation-free C chain/launch scheduler with fixed storage for four
  tracks and at most 16 entries per track. C host tests compile with MSVC
  `/W4 /WX /std:c11`; the CI job compiles with `cc -Wall -Wextra -Werror`.

## Remaining architectural gaps

1. **Firmware adapter:** `firmware/tracker_chain.[ch]` is in this repository but
   is not integrated into upstream SLOOP `events_block`, `seq_tick`, `trk_note_on`
   or `trk_note_off`. Its caller must use the existing transport row and turn
   changes into upstream note releases and phrase selection. It owns no clock or
   engine. No sound or device behavior has been verified.
2. **Slides and audio details:** SLOOP's slide/glide, voice stealing, exact
   ratchet/block rounding and instrument gate implementation have more engine
   context than the host adapter. Preserve flags and test against upstream C
   before claiming exact equivalence. Host gate timing is an integer ideal grid.
3. **Locks:** captured lock values and multi-lock ordering are preserved, and
   abstract apply/restore events are emitted. Engine base parameters are owned
   outside the model, so actual restoration requires the firmware callback.
4. **Pattern data:** display rows remain intentionally lossy projections, but the
   canonical `SourceStep` and raw protocol step tuples retain captured musical
   data. Existing `compile_chains` and `compile_arrangement` still accept only
   `Cell`; callers with captured source must use `CapturedChainPerformance`.
5. **Build:** the upstream checkout pins SLOOP 2.8 at
   `b77bf55e3bf804665b8f5dffb5955bd8443311f0`. Its `build.sh` requires JieLi's
   `pi32v2` compiler, the AC79 SDK, and Pillow. All three prerequisites were
   absent. An attempt to invoke the script through installed Git Bash failed before build
   startup because Bash could not create its Windows signal pipe (`Win32 error
   5`). The portable C module compiled and passed its host test under Visual
   Studio; this is not a SLOOP firmware build or image.
6. **Hardware:** no FM-1 was flashed or exercised. Audio deadlines, bootloader,
   sample playback, recording, keyboard/MIDI, storage and project compatibility
   remain unverified by this repository's tests.

## Upstream source inspected

Inspected SLOOP 2.8 commit `b77bf55e3bf804665b8f5dffb5955bd8443311f0` in a
separate checkout. `firmware/src/core.h` defines packed chord/drum steps, note
levels, ratchets, fill conditions and microtiming. `firmware/src/seq.c` owns
`seq_tick`, `seq_ratchets`, step release, locks, recording, MIDI and external
clock behavior. Its `events_block` runs in the audio ISR and advances the
existing shared clock. `firmware/src/fx.c` calls it from `mix_block`;
`firmware/src/audio.c` owns DMA/I2S rendering. `firmware/src/drums.c` provides
the lane mapping and `lvl_vel` level conversion. Those files were inspected;
none were modified or copied. SLOOP code is GPL-3.0-only and assets have separate
terms, documented in the upstream `LICENSE` and `LICENSING.md`.

## Verification

The existing Python suite grew from 80 to **94 passing tests**. Added coverage
for lossless synth/drum capture, level mapping, captured independent chains,
quantized/manual launches, gates, ties, continuation, fill conditions, lock
restoration and transition behavior. The standalone C harness compiled with
MSVC C11, `/W4 /WX`, and ran successfully; the state uses 520 bytes and its
static assertion bounds the scheduler state at 640 bytes. GitHub Actions now compiles/runs the same C harness
with strict `cc` warnings. The upstream AC79 firmware build could not run for
the missing Pillow, toolchain and SDK; the Windows shell also failed to start
the script. There is no flashable FM-Tracker image.

## Recommended next milestone

Integrate the reviewed C selector into a pinned SLOOP 2.8 working tree at its
existing `events_block`/transport boundary. First adapt one synth track and
prove note release and quantized selection against SLOOP's current scheduler;
then add drums and editor/storage mapping. Run upstream host audio/sequencer
regressions and build with the official JieLi compiler/SDK before any hardware
session. Keep the model-to-C event comparisons as a gate for each feature.
