# SLOOP integration notes

Upstream: https://github.com/isod89/sloop-fm1

Public documentation (checked October 2026) describes SLOOP 2.6:
- JieLi AC79 firmware with a host-side test suite
- 3 synth tracks with 8 shared synth voices, plus a 6-voice drum pool
- 44.1 kHz fixed-point DSP
- 64 steps per track, independent lengths/divisions, locks and microtiming
- USB MIDI, USB audio, and web editor protocol

## Integration strategy
1. Keep Python as an executable *reference model*, not production firmware.
2. Audit firmware source and storage formats; identify scheduler callback, audio event queue, display driver, and input scanner.
3. Port a small bounded C tracker scheduler to the existing audio timing domain.
4. Build host regression tests comparing C event output with reference-model fixtures.
5. Integrate a minimal tracker page, initially four tracks, before expanding logical tracks.
6. Measure worst-case event density, SRAM usage, flash size and audio deadline misses.

## Licensing
SLOOP is GPL-3.0. Review upstream LICENSE, LICENSING.md and third-party asset licenses before importing source. Maintain attribution and applicable source-distribution obligations.

## Hardware safety
No firmware flashing until a recovery method and known-good backup have been verified.
