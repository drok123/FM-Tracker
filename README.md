# FM-Tracker

Experimental tracker sequencer and sampler firmware for the M-VAVE FM-1.

## Traditional tracker screen

The opt-in tracker mode uses SLOOP's native phrase bank. Hold HOME, select the
SEQ menu section, choose TRACKER MODE with PRESETS, and tap OCT+. SLOOP still
starts normally. See [controls, connected functions, limits, and validation](docs/TRACKER_SCREEN.md).
This candidate was installed after explicit user approval; a fresh handshake
reports FM-1_900. Tracker screen interaction and audio still need hands-on
validation. The earlier hardware-tested build is archived for rollback.

## Status
**Native SLOOP overlay target-compiled and installed; playback not yet tested.** The pinned SLOOP
patch adds a per-track native phrase bank and invokes chain transitions from
SLOOP's existing `events_block`/`seq_tick` path. A JieLi AC79 build produces
`work/sloop-fm1/build/felucca.fwsc`; the local SLOOP installer preflight checks
its package identity, loader marker, and CRCs. The device accepted the update
from factory identity `FM-1_014` over USB-MIDI and now reports `FM-1_900`.
Tracker playback and audio behavior remain unverified on the device.

Captured SLOOP playback now shares fine timing with the offline preview and
preserves chords, per-note/lane dynamics, ratchets and microtiming across live
phrase switches. This is verified only as abstract host events. See the
[playback contract](docs/CAPTURED_PLAYBACK.md) and [architecture audit](docs/AUDIT.md)
for supported behavior and the remaining firmware integration gaps.

## Design goals
- Tracker-style phrase, chain, and song sequencing
- Up to 32 logical tracks as an initial software design target (not a measured hardware limit)
- Per-row note, instrument, volume, and effect commands
- Independent pattern lengths, deterministic timing, and MIDI output
- Sample slicing and instrument modulation tables
- Reuse compatible SLOOP audio engines where licensing and architecture permit

## Architecture
1. **Tracker core:** portable, deterministic event scheduler with no hardware dependencies.
2. **Instrument layer:** dispatch note/effect events to synth, sample, and MIDI backends.
3. **FM-1 adapter:** buttons, display, storage, timing, and audio integration.
4. **Editor/test harness:** run patterns and verify event timelines on a desktop before hardware flashing.

## Current milestone
The Python source model and event preview preserve captured SLOOP steps. The
native overlay copies all SLOOP step fields into an independent per-track phrase
bank and advances chains from SLOOP's current transport immediately before its
sequencer runs. CI exercises the actual SLOOP host path and stock mode; the
target build succeeded, while device behavior remains unverified. See the
[native integration notes](docs/NATIVE_SLOOP_INTEGRATION.md) and
[audit](docs/AUDIT.md) for scope and remaining work.

The successful target build's package, app, loader, patch, and disassembly hashes
are recorded in [build-manifest.json](build-manifest.json). Verify the package
SHA-256 there before using the installer.

After applying the pinned patch to the matching local SLOOP 2.8 checkout, validate
the built package without contacting the FM-1 with:

```sh
python3 tools/fm1_install.py build/felucca.fwsc --fm-tracker --verify-only
```

This profile requires product identity `FM-1_900`, the Felucca loader marker,
and valid package CRCs. The ordinary SLOOP two-stage updater code accepts a
running FM-1 identity such as factory `FM-1_015`; the simulator exercises that
route, but the factory updater handshake has not been verified on hardware. A
successful preflight or simulator test does not mean the firmware is installed.

## Safety
Do not flash unverified images. Preserve an official recovery procedure and known-good firmware before any device testing.

## Upstream and licensing
SLOOP is an upstream inspiration and possible integration base. Verify its exact repository, version, dependencies, and license before copying source. Any GPL-covered derivatives must comply with applicable license obligations.
