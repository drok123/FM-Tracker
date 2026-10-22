# Tracker-first architecture audit and prototype

Inspected against SLOOP 2.8 commit
`b77bf55e3bf804665b8f5dffb5955bd8443311f0`, with the existing FM-Tracker overlay.
The source change is carried in `patches/sloop-fm1-2.8-tracker.patch`.

## Boundary: retain infrastructure, replace the application incrementally

SLOOP is a useful firmware foundation, not a requirement to keep its page and
layer navigation as FM-Tracker's primary workflow. Its source is one C
translation unit (`felucca.c`), so the practical seam is an application module
and explicit keyboard-routing hooks. This prototype does not claim that the
audio and application layers are already separate libraries.

| Area | Actual source boundary | Treatment in this prototype |
| --- | --- | --- |
| Hardware and recovery | `firmware/hal/fm1_{sys,time,irq,input,timer,audio,adc,lcd_hw,cpu1,flash,xip}.h`, startup assembly, linker layout, `ota.c`, `recovery.c` | Retain register access, timings, boot guards, firmware update/recovery protocol and storage regions |
| Input scan and LEDs | `fm1_input.h`, calibrated `panel.c` | Retain matrix scan/debounce, encoder decoding, key ownership and persisted brightness/calibration; add tracker step-LED content through the existing LED renderer |
| Display and graphics | `lcd.c`, `gfx.c` | Retain SPI/DMA synchronization, RGB565, fonts, small canvas; replace product screen content |
| Audio and instruments | `audio.c`, `voice.c`, `engines.c`, `eng_fm6.c`, `eng_sample.c`, `drums.c`, `fx.c`, `cpu1.c` | Retain sound engines, voice allocation/release, native FM/sample playback, mixing and effects |
| Timing, notes, recording | `seq.c`: `mix_block/events_block`, `seq_tick`, `seq_step`, `drum_step`, `input_on/off`, `rec_toggle`, `rec_note` | Retain the sole clock/sequencer/recorder. Change keyboard intent routing only; native held-note releases remain authoritative |
| Live sequence model | `core.h`: `track_t`, native step/drum union; `project.c` | Edit native `trk[]` patterns directly, so PLAY needs no scene or phrase capture/load. Reuse undo and existing autosave/project format |
| Phrase and chain layer | `fm_tracker_bank.*`, `tracker_chain.*`, `tracker_sloop_adapter.*`, native transition hooks in `seq.c` | Retain existing bank and runtime APIs. The primary editor adds no second pattern or chain runtime and does not silently synchronize bank slots |
| Existing application | `ui*.c`, page definitions in `params.c`, `arranger.c` | Keep as fallback. Tracker has its own screen and control dispatch, temporarily selects loop playback, and restores the fallback's arranger enable setting on exit |
| Mixed application helpers | preset application/track selection/undo in `ui.c`; MIDI polling and held-button handling in `ui_input.c` | Reuse helpers rather than deleting these files. Their mixed responsibilities require careful later extraction |
| Startup | `main.c:felucca_init`, startup splash selection | Restore normal native project/settings, initialize engines, then open FM-Tracker by default. SLOOP remains a fallback and a compile-time startup option |
| USB/MIDI/editor | `usb.c`, `midi_uart.c`, `editor*.c` | Retain communication and editor compatibility. No new sample input or incompatible file format is introduced |

## Physical controls and display

The current HAL defines an **11-column, six-row matrix**, **27 note keys**
(key indices 0..26, F3..G5 before octave/scale mapping), **14 function buttons**
and **seven encoders**. The `FM1_NCOL` implementation and `FM1_KEYMAP` take
precedence over stale comments or host-test dummy matrix dimensions.

There are **16 white keys**, mapped with native `key_of_white/key_of_lane`,
and 11 black keys. The white keys are steps in STEP mode; black keys do not
alias a white step. In NOTE mode, all keys use the existing keyboard mapping,
including octave/scale settings; the drum track uses its existing lane map.

`panel.c` defaults: SELECT encoder 0, ALGORITHM 1, PRESETS 6, KNOB 1..4
encoders 2..5. HOME/SEQ/PLAY/REC matrix button IDs are 8/11/12/13; OCT-/OCT+
are 0/1. All actual control access uses the user's calibrated panel table,
not these raw IDs.

The display is **240 x 240**, ST7789-class, with 8 x 16 small text. The canvas
is limited to **240 x 124 RGB565 pixels**. The prototype uses short strips,
eight visible rows and all four physical tracks; the selected column is 72
pixels wide, others 48, plus 24 for row numbers. It caches individual rows and
header/detail/footer strips instead of transmitting a complete framebuffer
every audio step. Display calls remain outside the audio interrupt.

## Keyboard ownership and mutation safety

SLOOP normally interprets held function buttons inside `seq.c:layer_now`,
independently of UI navigation. Merely replacing the screen would leave
hidden erase, roll, punch, or step-entry actions active. Tracker routing
therefore bypasses those held-button layers only while its application is
active; fallback behavior remains unchanged.

STEP key-down/up intent travels through the existing bounded `lk_q` ring.
Events retain the originating track, and only the main loop mutates patterns.
Press selects a row; release toggles it, unless a knob edited the held row.
This makes tap-versus-hold explicit and avoids accidentally deleting an edited
step on release. With multiple keys held, knobs edit the most recently
selected row. The native undo snapshot covers that gesture.

NOTE key-down adds an editor event containing the actual mapped pitch or drum
lane, while the existing synth/drum key path still handles audition and note
release. Stopped/disarmed programming inserts a note/hit at the cursor and
advances one row per key press, wrapping at the native track length. This first
version enters single notes, not a new chord-collection algorithm. Existing
chords elsewhere are preserved; pitch/velocity/ratchet knob edits preserve
other chord voices and unrelated flags.

The stopped editor is gated during playback, pending transport, recording,
count-in and free takes. Native REC switches to NOTE mode and uses the existing
live recorder. NOTE keys audition during playback; direct tracker programming
does not compete with recording. Small native mutations and undo snapshots
are protected with the existing IRQ mask. No flash writes occur per key press;
normal autosave remains responsible for persistence.

Queue overflow cancels pending editor gestures and displays a retry message;
it cannot become a random step toggle. Synth note release does not depend on
successful delivery of an editor event. Track changes and mode/fallback
switches cancel pending gestures; native key-up ownership remains intact.

## Instruments, storage and sampling limits

- There are four physical tracks: three general instrument parts and a drum
  part, with **64 native rows per track**. The synth parts share an eight-voice
  budget; the drum engine has its own pool. This is not a 32-track hardware
  claim.
- FM6 and sample engines already exist; PRESETS browses the native sound
  library across engines on a general part. The screen shows the real engine
  name. Startup sound choices are preserved rather than labeling every part
  as an FM voice regardless of its actual engine.
- Instruments are currently assigned per track, not per row. A future tracker
  instrument table must dispatch through the existing engine/voice lifecycle
  and define its storage format before per-row instrument IDs are meaningful.
- User samples already occupy four 80 KiB flash slots (`SMP_USER_SIZE=0x14000`),
  with 512-byte header/data offset and up to 16 zones each, using IMA ADPCM and
  XIP reads. USR1..3 start at `0xA0000`; USR4 starts at `0xE7000`.
  These are reserved user-data regions, not free firmware space.
- The previous installed add-on build used 72,760 / 98,304 bytes in the RAM
  data/BSS region, 22,772 / 29,488 low RAM, and 333,900 / 344,064 pool bytes,
  leaving **10,164 pool bytes** (the builder requires at least 8,192). The app
  slot is `0x8DFBC` bytes. The new build's exact usage is in its manifest.
  These linker regions are distinct and cannot be casually combined into one
  sampling-buffer budget.
- `fm1_audio.h` configures outgoing ALNK/I2S audio to the codec.
  `fm1_adc.h` reads control/battery ADC channels, not a demonstrated audio ADC
  capture stream. `usb.c` presents the FM-1 mix as a USB recording/input device
  **to the computer**; this does not establish an incoming sample stream on
  the FM-1. Analog audio input/codec ADC wiring and usable capture DMA still
  need hardware investigation. Native REC presently records musical events,
  not microphone/line audio.

## Next boundaries to extract

1. Validate primary navigation, step/note ownership, recording and fallbacks on
   hardware with the preserved previous image available.
2. Extract a small native pattern-edit API from the mixed UI helpers, including
   revision notifications and richer undo. Keep the existing sequencer clock.
3. Add deliberate pattern/phrase selection and chains using the retained bank
   and scheduler; define save/load semantics and migrations before persistence.
4. Define instrument IDs that can select FM or samples through the native sound
   system. Existing per-track sound browsing already provides both.
5. Measure worst-case audio deadlines, stack usage and target RAM before any
   sampler/capture allocation; audit actual incoming audio hardware separately.

This is an application prototype, not a replacement for the drivers or a
claim of new hardware capabilities. GPL notices and upstream attribution stay
in the overlay and source documentation.
