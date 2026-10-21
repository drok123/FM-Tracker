# FM-Tracker

Experimental tracker sequencer and sampler firmware for the M-VAVE FM-1.

## Status
**Research / host-side prototype.** No flashable firmware is provided yet. Hardware capabilities and compatibility must be verified against upstream SLOOP source and an actual FM-1.

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

## First milestone
Implement a host-testable tracker event model, row/tick scheduler, and regression tests. Audit SLOOP source for CPU, RAM, sample storage, display, and bootloader constraints before attempting firmware integration.

## Safety
Do not flash unverified images. Preserve an official recovery procedure and known-good firmware before any device testing.

## Upstream and licensing
SLOOP is an upstream inspiration and possible integration base. Verify its exact repository, version, dependencies, and license before copying source. Any GPL-covered derivatives must comply with applicable license obligations.
