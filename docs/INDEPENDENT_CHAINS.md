# Fast Track: independent chains

Host reference implementation. Each track's chain has independent entries,
repeat counts, phrase durations and optional looping. A chain can stop while
another continues. This is a separate arrangement mode from the earlier
globally aligned song positions.

A phrase entry's `rows` controls how long it occupies the timeline; the
phrase's own cells wrap during that time. Transposition is non-destructive.
Silence is represented by a null phrase.

Current limitations: no note-offs, live queueing, quantized launch, or SLOOP
firmware scheduling integration. Chords/drums from SLOOP capture remain outside
the simple single-note compiler. Hardware and timing tests are required.
