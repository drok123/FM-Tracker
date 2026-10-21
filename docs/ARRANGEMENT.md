# Fast Track pattern chaining

Host-side proof of concept, not FM-1 firmware.

## Model
- **Phrase:** reusable named sequence of tracker cells.
- **Chain slot:** phrase reference, transpose offset, mute.
- **Song position:** simultaneous slots for all logical tracks and a duration in rows.
- **Arrangement:** ordered song positions and phrase library.

Phrases wrap at their own lengths within a song position, permitting polymeter.
At the next position boundary, each track selects its next phrase or silence.
The source phrase remains immutable when transposed.

## Next work
- Support per-track independent chain advancement, not only global song positions.
- Add loop counts, jump/stop markers, live chain launch quantization.
- Wire phrase library to Fast Track's SLOOP capture representation.
- Preserve SLOOP chord/drum/lock semantics: current simple tracker compiler only
  schedules its single-note Cell projection, not full source patterns.
- Add note-off and voice-ownership handling at transitions.
- Evaluate compatibility with upstream SLOOP's existing section chain feature.
- Run tests and benchmark resource usage before porting to embedded C.

No firmware modifications or flashing in this commit.
