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

1. **Firmware integration:** `firmware/tracker_sloop_adapter.[ch]` now provides
   a bounded callback boundary over the scheduler. It accepts rows from SLOOP's
   existing transport and sends per-track phrase transitions to the caller.
   Control-side configuration requires SLOOP IRQ save/restore callbacks to
   protect it from the audio callback. A fake-SLOOP harness covers independent
   selection, quantized launches, track stop, restart cleanup and row-gap
   rejection. The upstream
   `felucca.c` / `seq.c` files are still unmodified: the callback has not yet
   been connected to `events_block`, `seq_release`, lock restoration or
   per-track scene loading, so this is not an integrated firmware feature.
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
restoration and transition behavior. The existing standalone chain harness
previously compiled with MSVC C11, `/W4 /WX`, and ran successfully; its state
uses 520 bytes and is bounded at 640 bytes. The new SLOOP boundary adapter is
568 bytes on the Ubuntu 24.04 x86-64 CI runner; this is a host size, not the
target's 32-bit memory measurement. This environment has no `cl`, `clang`,
`gcc`, or `cc`, so the C checks ran in CI instead of locally. The run on commit
`ae31d8513897fd5598a857cb0e0ceaedd5f286aa` passed all 94 Python tests, both
strict-warning C harnesses, and both AddressSanitizer/UBSan harness runs.
Locally, `unittest` also passed 94 tests. `pytest` is not installed, and an
isolated attempt to install `pytest` and Pillow stalled during package metadata
download. The target build cannot proceed here: `JIELI_TOOLCHAIN` and the JieLi
AC79 SDK are absent. Upstream documents these prerequisites:

- Pillow for the Python build tools.
- `JIELI_TOOLCHAIN` with `pi32v2/bin/clang`; `tools/get_toolchain.sh` downloads
  JieLi's Linux toolchain from its documented package server.
- JieLi's AC79 SDK release `AC79NN_SDK_V1.2.1_2023-12-13` from the official
  Gitee repository. The package requires `cpu/wl82/tools/uboot.boot`,
  `cfg_tool.bin`, and `cfg/eq_cfg_hw.bin`.
- On Windows, the upstream instructions require WSL with the toolchain and SDK;
  `SLOOP_WSL_DISTRO` and `SLOOP_TOOLCHAIN` select the WSL environment.

The available upstream command `python tools/build.py` stops because
`cpu/wl82/tools/uboot.boot` is missing. No target firmware or package size was
produced, and there is no flashable FM-Tracker image.

## Recommended next milestone

Connect the callback in `firmware/tracker_sloop_adapter.[ch]` to a pinned SLOOP
2.8 source tree. `events_block` should derive the adapter row from `clk_beat` and
`clk_pos`, then invoke transitions before `seq_tick`; a track transition must
restore that track's locks, release notes through SLOOP's APIs, and select only
that track's source phrase. The current four-project scene store is whole-project
data, so a safe per-track phrase source and UI/storage mapping still need design.
Run upstream host audio/sequencer regressions and build with the official JieLi
compiler/SDK before claiming firmware functionality.
