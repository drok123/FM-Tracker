/* SPDX-License-Identifier: GPL-3.0-only
 * FM-Tracker boundary adapter for SLOOP's existing audio-block sequencer.
 * The caller supplies SLOOP's transport row; this module never owns a clock.
 */
#ifndef FM_TRACKER_SLOOP_ADAPTER_H
#define FM_TRACKER_SLOOP_ADAPTER_H

#include "tracker_chain.h"

typedef struct {
    /* Required for control-thread changes while SLOOP audio is active. Map to
     * SLOOP's IRQ save/restore pair; the row callback itself runs in that ISR. */
    uint32_t (*control_lock)(void *user);
    void (*control_unlock)(void *user, uint32_t token);
    /* Called in the audio-block context, before SLOOP advances that track's
     * sequencer. Implementations must release/retain notes using SLOOP's own
     * seq_release/trk_note_off semantics, restore locks, and select only this
     * track's phrase. A stopped change has phrase == FM_TRACKER_NO_PHRASE. */
    void (*transition)(void *user, uint8_t track, int16_t old_phrase,
                       int8_t old_transpose, int16_t phrase,
                       int8_t transpose, uint8_t stopped);
} fm_tracker_sloop_ops_t;

typedef struct {
    fm_tracker_t scheduler;
    fm_tracker_sloop_ops_t ops;
    void *user;
    int16_t active_phrase[FM_TRACKER_TRACKS];
    int8_t active_transpose[FM_TRACKER_TRACKS];
} fm_tracker_sloop_t;

void fm_tracker_sloop_init(fm_tracker_sloop_t *adapter,
                           const fm_tracker_sloop_ops_t *ops, void *user);
int fm_tracker_sloop_set_chain(fm_tracker_sloop_t *adapter, uint8_t track,
                               const fm_tracker_entry_t *entries,
                               uint8_t count, uint8_t loop);
int fm_tracker_sloop_start_chain(fm_tracker_sloop_t *adapter, uint8_t track,
                                 uint32_t at_row);
int fm_tracker_sloop_stop_track(fm_tracker_sloop_t *adapter, uint8_t track,
                                uint32_t at_row);
int fm_tracker_sloop_queue_launch(fm_tracker_sloop_t *adapter, uint8_t track,
                                  int16_t phrase, int8_t transpose,
                                  uint32_t at_row);
int fm_tracker_sloop_queue_quantized(fm_tracker_sloop_t *adapter,
                                     uint8_t track, int16_t phrase,
                                     int8_t transpose, uint32_t requested_row,
                                     fm_tracker_quantum_t quantum,
                                     uint16_t rows_per_beat,
                                     uint16_t beats_per_bar,
                                     uint16_t phrase_rows);
/* End all current phrase ownership and return to row zero while retaining the
 * configured chains. SLOOP should call this on stop/restart clock reset. */
void fm_tracker_sloop_transport_reset(fm_tracker_sloop_t *adapter);
/* Invoke once per SLOOP transport row from its existing events_block path.
 * Returns 1 when processed, 0 on an invalid/discontinuous row. */
int fm_tracker_sloop_row(fm_tracker_sloop_t *adapter, uint32_t transport_row);

#endif
