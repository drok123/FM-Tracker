/* SPDX-License-Identifier: GPL-3.0-only
 * FM-Tracker bounded chain/launch state for host verification and SLOOP porting.
 * This module never advances the transport and has no audio or engine calls.
 */
#ifndef FM_TRACKER_CHAIN_H
#define FM_TRACKER_CHAIN_H

#include <stdint.h>

#define FM_TRACKER_TRACKS 4u
#define FM_TRACKER_CHAIN_ENTRIES 16u
#define FM_TRACKER_NO_PHRASE INT16_C(-1)

typedef struct {
    int16_t phrase;
    uint16_t rows;
    uint8_t repeats;
    int8_t transpose;
} fm_tracker_entry_t;

typedef struct {
    uint8_t count;
    uint8_t loop;
    fm_tracker_entry_t entries[FM_TRACKER_CHAIN_ENTRIES];
} fm_tracker_chain_t;

typedef struct {
    int16_t phrase;
    int8_t transpose;
    uint32_t at_row;
    uint8_t pending;
} fm_tracker_launch_t;

typedef struct {
    fm_tracker_chain_t chain;
    uint8_t chain_running;
    uint8_t chain_start_pending;
    uint32_t chain_start_row;
    uint8_t position;
    uint8_t repeat;
    uint8_t active;
    int16_t phrase;
    int8_t transpose;
    uint32_t entry_start_row;
    fm_tracker_launch_t launch;
} fm_tracker_track_t;

typedef struct {
    fm_tracker_track_t tracks[FM_TRACKER_TRACKS];
    uint32_t last_row;
    uint8_t have_row;
} fm_tracker_t;

typedef struct {
    uint8_t changed;
    uint8_t stopped;
    int16_t phrase;
    int8_t transpose;
} fm_tracker_change_t;

typedef enum {
    FM_TRACKER_ROW = 0,
    FM_TRACKER_BEAT = 1,
    FM_TRACKER_BAR = 2,
    FM_TRACKER_PHRASE = 3
} fm_tracker_quantum_t;

void fm_tracker_init(fm_tracker_t *tracker);
/* Clear active chain/launch runtime while preserving configured chains. */
void fm_tracker_transport_reset(fm_tracker_t *tracker);
int fm_tracker_set_chain(fm_tracker_t *tracker, uint8_t track,
                         const fm_tracker_entry_t *entries, uint8_t count,
                         uint8_t loop);
int fm_tracker_start_chain(fm_tracker_t *tracker, uint8_t track,
                           uint32_t at_row);
int fm_tracker_stop_track(fm_tracker_t *tracker, uint8_t track,
                          uint32_t at_row);
int fm_tracker_queue_launch(fm_tracker_t *tracker, uint8_t track,
                            int16_t phrase, int8_t transpose,
                            uint32_t at_row);
int fm_tracker_quantize_row(uint32_t requested_row, fm_tracker_quantum_t quantum,
                            uint16_t rows_per_beat, uint16_t beats_per_bar,
                            uint16_t phrase_rows, uint32_t *scheduled_row);
int fm_tracker_queue_quantized(fm_tracker_t *tracker, uint8_t track,
                               int16_t phrase, int8_t transpose,
                               uint32_t requested_row, fm_tracker_quantum_t quantum,
                               uint16_t rows_per_beat, uint16_t beats_per_bar,
                               uint16_t phrase_rows);
/* Call once per advancing row, detected from SLOOP's existing transport in its
 * event callback. Rows must stay monotonic and consecutive; no clock is owned
 * or advanced here. */
int fm_tracker_advance(fm_tracker_t *tracker, uint32_t transport_row,
                       fm_tracker_change_t changes[FM_TRACKER_TRACKS]);

#endif
