# FM-Tracker

Experimental tracker sequencer and sampler firmware for the M-VAVE FM-1.

## Tracker-first prototype

FM-Tracker now starts in its own four-track pattern editor. SEQ switches the
physical keys between white-key step entry and pitched note entry; holding a
step lets the four knobs edit it. Native SLOOP synthesis, sample playback,
recording, timing and project data remain underneath the application. Hold
HOME to open the SLOOP fallback.

See the [hardware/application audit](docs/TRACKER_FIRST_AUDIT.md) and
[actual controls, limitations and validation](docs/TRACKER_SCREEN.md).
The tracker-first candidate is not installed. The previously installed
tracker-add-on package is preserved for rollback, along with the earlier
SLOOP-startup build. See [build-manifest.json](build-manifest.json) for the exact
candidate, verification results and device status.

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

## Retained native foundation
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
