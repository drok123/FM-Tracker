/* SPDX-License-Identifier: GPL-3.0-only */
#include "tracker_chain.h"

#include <stddef.h>
#include <string.h>

static void change_to(fm_tracker_track_t *track, int16_t phrase,
                      int8_t transpose, uint32_t row,
                      fm_tracker_change_t *change)
{
    track->active = phrase >= 0;
    track->phrase = track->active ? phrase : FM_TRACKER_NO_PHRASE;
    track->transpose = track->active ? transpose : 0;
    track->entry_start_row = row;
    change->changed = 1u;
    change->stopped = (uint8_t)!track->active;
    change->phrase = track->phrase;
    change->transpose = track->transpose;
}

void fm_tracker_init(fm_tracker_t *tracker)
{
    uint8_t i;
    if (tracker != NULL) {
        memset(tracker, 0, sizeof(*tracker));
        for (i = 0u; i < FM_TRACKER_TRACKS; ++i)
            tracker->tracks[i].phrase = FM_TRACKER_NO_PHRASE;
    }
}

void fm_tracker_transport_reset(fm_tracker_t *tracker)
{
    uint8_t i;
    if (tracker == NULL)
        return;
    for (i = 0u; i < FM_TRACKER_TRACKS; ++i) {
        fm_tracker_track_t *state = &tracker->tracks[i];
        memset(&state->chain_running, 0,
               sizeof(*state) - offsetof(fm_tracker_track_t, chain_running));
        state->phrase = FM_TRACKER_NO_PHRASE;
    }
    tracker->last_row = 0u;
    tracker->have_row = 0u;
}

int fm_tracker_set_chain(fm_tracker_t *tracker, uint8_t track,
                         const fm_tracker_entry_t *entries, uint8_t count,
                         uint8_t loop)
{
    uint8_t i;
    if (tracker == NULL || track >= FM_TRACKER_TRACKS ||
        count > FM_TRACKER_CHAIN_ENTRIES || (count != 0u && entries == NULL) ||
        loop > 1u)
        return 0;
    for (i = 0u; i < count; ++i)
        if (entries[i].phrase < 0 || entries[i].rows == 0u ||
            entries[i].repeats == 0u)
            return 0;
    memset(&tracker->tracks[track].chain, 0,
           sizeof(tracker->tracks[track].chain));
    if (count != 0u)
        memcpy(tracker->tracks[track].chain.entries, entries,
               (size_t)count * sizeof(*entries));
    tracker->tracks[track].chain.count = count;
    tracker->tracks[track].chain.loop = loop;
    tracker->tracks[track].chain_running = 0u;
    tracker->tracks[track].chain_start_pending = 0u;
    return 1;
}

int fm_tracker_start_chain(fm_tracker_t *tracker, uint8_t track,
                           uint32_t at_row)
{
    fm_tracker_track_t *state;
    if (tracker == NULL || track >= FM_TRACKER_TRACKS)
        return 0;
    state = &tracker->tracks[track];
    if (state->chain.count == 0u ||
        (tracker->have_row && at_row <= tracker->last_row))
        return 0;
    state->chain_running = 1u;
    state->chain_start_pending = 1u;
    state->chain_start_row = at_row;
    state->position = 0u;
    state->repeat = 0u;
    state->launch.pending = 0u;
    return 1;
}

int fm_tracker_stop_track(fm_tracker_t *tracker, uint8_t track,
                          uint32_t at_row)
{
    fm_tracker_track_t *state;
    if (tracker == NULL || track >= FM_TRACKER_TRACKS)
        return 0;
    if (tracker->have_row && at_row <= tracker->last_row)
        return 0;
    state = &tracker->tracks[track];
    state->launch.pending = 1u;
    state->launch.phrase = FM_TRACKER_NO_PHRASE;
    state->launch.transpose = 0;
    state->launch.at_row = at_row;
    return 1;
}

int fm_tracker_queue_launch(fm_tracker_t *tracker, uint8_t track,
                            int16_t phrase, int8_t transpose,
                            uint32_t at_row)
{
    fm_tracker_track_t *state;
    if (tracker == NULL || track >= FM_TRACKER_TRACKS || phrase < -1 ||
        (tracker->have_row && at_row <= tracker->last_row))
        return 0;
    state = &tracker->tracks[track];
    state->launch.pending = 1u;
    state->launch.phrase = phrase;
    state->launch.at_row = at_row;
    state->launch.transpose = transpose;
    return 1;
}

int fm_tracker_quantize_row(uint32_t requested_row, fm_tracker_quantum_t quantum,
                            uint16_t rows_per_beat, uint16_t beats_per_bar,
                            uint16_t phrase_rows, uint32_t *scheduled_row)
{
    uint32_t grid;
    uint32_t remainder;
    if (scheduled_row == NULL || rows_per_beat == 0u || beats_per_bar == 0u ||
        phrase_rows == 0u)
        return 0;
    switch (quantum) {
    case FM_TRACKER_ROW:
        grid = 1u;
        break;
    case FM_TRACKER_BEAT:
        grid = rows_per_beat;
        break;
    case FM_TRACKER_BAR:
        grid = (uint32_t)rows_per_beat * beats_per_bar;
        break;
    case FM_TRACKER_PHRASE:
        grid = phrase_rows;
        break;
    default:
        return 0;
    }
    remainder = requested_row % grid;
    if (remainder != 0u) {
        uint32_t addition = grid - remainder;
        if (UINT32_MAX - requested_row < addition)
            return 0;
        requested_row += addition;
    }
    *scheduled_row = requested_row;
    return 1;
}

int fm_tracker_queue_quantized(fm_tracker_t *tracker, uint8_t track,
                               int16_t phrase, int8_t transpose,
                               uint32_t requested_row, fm_tracker_quantum_t quantum,
                               uint16_t rows_per_beat, uint16_t beats_per_bar,
                               uint16_t phrase_rows)
{
    uint32_t scheduled;
    if (!fm_tracker_quantize_row(requested_row, quantum, rows_per_beat,
                                 beats_per_bar, phrase_rows, &scheduled))
        return 0;
    return fm_tracker_queue_launch(tracker, track, phrase, transpose, scheduled);
}

static void chain_advance(fm_tracker_track_t *state, uint32_t row,
                          fm_tracker_change_t *change)
{
    fm_tracker_chain_t *chain = &state->chain;
    fm_tracker_entry_t *entry;
    if (state->chain_start_pending) {
        if (state->chain_start_row > row)
            return;
        entry = &chain->entries[0];
        state->chain_start_pending = 0u;
        state->position = 0u;
        state->repeat = 0u;
        change_to(state, entry->phrase, entry->transpose, row, change);
        return;
    }
    if (!state->chain_running || state->position >= chain->count)
        return;
    entry = &chain->entries[state->position];
    if (row - state->entry_start_row < entry->rows)
        return;
    if (++state->repeat < entry->repeats) {
        change_to(state, entry->phrase, entry->transpose, row, change);
        return;
    }
    state->repeat = 0u;
    if (++state->position >= chain->count) {
        if (!chain->loop) {
            state->chain_running = 0u;
            change_to(state, FM_TRACKER_NO_PHRASE, 0, row, change);
            return;
        }
        state->position = 0u;
    }
    entry = &chain->entries[state->position];
    change_to(state, entry->phrase, entry->transpose, row, change);
}

int fm_tracker_advance(fm_tracker_t *tracker, uint32_t transport_row,
                       fm_tracker_change_t changes[FM_TRACKER_TRACKS])
{
    uint8_t i;
    if (tracker == NULL || changes == NULL)
        return 0;
    if (tracker->have_row &&
        (transport_row < tracker->last_row ||
         (tracker->last_row != UINT32_MAX && transport_row > tracker->last_row + 1u)))
        return 0;
    memset(changes, 0, sizeof(*changes) * FM_TRACKER_TRACKS);
    tracker->last_row = transport_row;
    tracker->have_row = 1u;
    for (i = 0u; i < FM_TRACKER_TRACKS; ++i) {
        fm_tracker_track_t *state = &tracker->tracks[i];
        fm_tracker_change_t *change = &changes[i];
        if (state->launch.pending && state->launch.at_row <= transport_row) {
            int16_t phrase = state->launch.phrase;
            int8_t transpose = state->launch.transpose;
            state->launch.pending = 0u;
            state->chain_running = 0u;
            state->chain_start_pending = 0u;
            change_to(state, phrase, transpose, transport_row, change);
        } else {
            chain_advance(state, transport_row, change);
        }
    }
    return 1;
}
