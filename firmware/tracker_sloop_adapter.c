/* SPDX-License-Identifier: GPL-3.0-only */
#include "tracker_sloop_adapter.h"

#include <string.h>

static int control_lock(fm_tracker_sloop_t *adapter, uint32_t *token)
{
    if (adapter->ops.control_lock == NULL || adapter->ops.control_unlock == NULL)
        return 0;
    *token = adapter->ops.control_lock(adapter->user);
    return 1;
}

static void control_unlock(fm_tracker_sloop_t *adapter, uint32_t token)
{
    adapter->ops.control_unlock(adapter->user, token);
}

void fm_tracker_sloop_init(fm_tracker_sloop_t *adapter,
                           const fm_tracker_sloop_ops_t *ops, void *user)
{
    uint8_t i;
    if (adapter == NULL)
        return;
    memset(adapter, 0, sizeof(*adapter));
    fm_tracker_init(&adapter->scheduler);
    if (ops != NULL)
        adapter->ops = *ops;
    adapter->user = user;
    for (i = 0; i < FM_TRACKER_TRACKS; ++i)
        adapter->active_phrase[i] = FM_TRACKER_NO_PHRASE;
}

int fm_tracker_sloop_set_chain(fm_tracker_sloop_t *adapter, uint8_t track,
                               const fm_tracker_entry_t *entries,
                               uint8_t count, uint8_t loop)
{
    uint32_t token;
    int result;
    if (adapter == NULL || !control_lock(adapter, &token))
        return 0;
    result = fm_tracker_set_chain(&adapter->scheduler, track, entries,
                                  count, loop);
    control_unlock(adapter, token);
    return result;
}

int fm_tracker_sloop_start_chain(fm_tracker_sloop_t *adapter, uint8_t track,
                                 uint32_t at_row)
{
    uint32_t token;
    int result;
    if (adapter == NULL || !control_lock(adapter, &token))
        return 0;
    result = fm_tracker_start_chain(&adapter->scheduler, track, at_row);
    control_unlock(adapter, token);
    return result;
}

int fm_tracker_sloop_stop_track(fm_tracker_sloop_t *adapter, uint8_t track,
                                uint32_t at_row)
{
    uint32_t token;
    int result;
    if (adapter == NULL || !control_lock(adapter, &token))
        return 0;
    result = fm_tracker_stop_track(&adapter->scheduler, track, at_row);
    control_unlock(adapter, token);
    return result;
}

int fm_tracker_sloop_queue_launch(fm_tracker_sloop_t *adapter, uint8_t track,
                                  int16_t phrase, int8_t transpose,
                                  uint32_t at_row)
{
    uint32_t token;
    int result;
    if (adapter == NULL || !control_lock(adapter, &token))
        return 0;
    result = fm_tracker_queue_launch(&adapter->scheduler, track, phrase,
                                     transpose, at_row);
    control_unlock(adapter, token);
    return result;
}

int fm_tracker_sloop_queue_quantized(fm_tracker_sloop_t *adapter,
                                     uint8_t track, int16_t phrase,
                                     int8_t transpose, uint32_t requested_row,
                                     fm_tracker_quantum_t quantum,
                                     uint16_t rows_per_beat,
                                     uint16_t beats_per_bar,
                                     uint16_t phrase_rows)
{
    uint32_t token;
    int result;
    if (adapter == NULL || !control_lock(adapter, &token))
        return 0;
    result = fm_tracker_queue_quantized(
        &adapter->scheduler, track, phrase, transpose, requested_row,
        quantum, rows_per_beat, beats_per_bar, phrase_rows);
    control_unlock(adapter, token);
    return result;
}

void fm_tracker_sloop_transport_reset(fm_tracker_sloop_t *adapter)
{
    uint8_t i;
    if (adapter == NULL)
        return;
    for (i = 0u; i < FM_TRACKER_TRACKS; ++i) {
        if (adapter->active_phrase[i] >= 0 && adapter->ops.transition != NULL)
            adapter->ops.transition(adapter->user, i, adapter->active_phrase[i],
                                    adapter->active_transpose[i],
                                    FM_TRACKER_NO_PHRASE, 0, 1u);
        adapter->active_phrase[i] = FM_TRACKER_NO_PHRASE;
        adapter->active_transpose[i] = 0;
    }
    fm_tracker_transport_reset(&adapter->scheduler);
}

int fm_tracker_sloop_row(fm_tracker_sloop_t *adapter, uint32_t transport_row)
{
    fm_tracker_change_t changes[FM_TRACKER_TRACKS];
    uint8_t i;
    if (adapter == NULL || !fm_tracker_advance(&adapter->scheduler,
                                                transport_row, changes))
        return 0;
    if (adapter->ops.transition == NULL)
        return 1;
    for (i = 0; i < FM_TRACKER_TRACKS; ++i) {
        const fm_tracker_change_t *c = &changes[i];
        if (c->changed) {
            adapter->ops.transition(adapter->user, i,
                                     adapter->active_phrase[i],
                                     adapter->active_transpose[i], c->phrase,
                                     c->transpose, c->stopped);
            adapter->active_phrase[i] = c->phrase;
            adapter->active_transpose[i] = c->transpose;
        }
    }
    return 1;
}
