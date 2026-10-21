#include "../firmware/tracker_sloop_adapter.h"

#include <assert.h>
#include <stdio.h>
#include <string.h>

typedef struct {
    unsigned calls[FM_TRACKER_TRACKS];
    unsigned lock_depth;
    int16_t phrase[FM_TRACKER_TRACKS];
    int8_t transpose[FM_TRACKER_TRACKS];
    uint8_t stopped[FM_TRACKER_TRACKS];
} fake_sloop_t;

static uint32_t control_lock(void *user)
{
    fake_sloop_t *fake = (fake_sloop_t *)user;
    fake->lock_depth++;
    return 0xA55Au;
}

static void control_unlock(void *user, uint32_t token)
{
    fake_sloop_t *fake = (fake_sloop_t *)user;
    assert(token == 0xA55Au && fake->lock_depth == 1u);
    fake->lock_depth--;
}

static void transition(void *user, uint8_t track, int16_t old_phrase,
                       int8_t old_transpose, int16_t phrase, int8_t transpose,
                       uint8_t stopped)
{
    fake_sloop_t *fake = (fake_sloop_t *)user;
    assert(track < FM_TRACKER_TRACKS);
    if (fake->calls[track]) {
        assert(old_phrase == fake->phrase[track]);
        assert(old_transpose == fake->transpose[track]);
    }
    fake->calls[track]++;
    fake->phrase[track] = phrase;
    fake->transpose[track] = transpose;
    fake->stopped[track] = stopped;
}

int main(void)
{
    fm_tracker_sloop_t adapter;
    fake_sloop_t fake;
    const fm_tracker_sloop_ops_t ops = {control_lock, control_unlock, transition};
    const fm_tracker_entry_t lead[] = {{2, 32, 1, 0}, {3, 32, 1, 5}};
    const fm_tracker_entry_t drums[] = {{1, 32, 2, 0}};
    unsigned i;
    memset(&fake, 0, sizeof fake);
    for (i = 0; i < FM_TRACKER_TRACKS; ++i)
        fake.phrase[i] = FM_TRACKER_NO_PHRASE;
    fm_tracker_sloop_init(&adapter, &ops, &fake);
    assert(fm_tracker_sloop_set_chain(&adapter, 0, lead, 2, 0));
    assert(fm_tracker_sloop_set_chain(&adapter, 3, drums, 1, 1));
    assert(fm_tracker_sloop_start_chain(&adapter, 0, 0));
    assert(fm_tracker_sloop_start_chain(&adapter, 3, 0));
    assert(fake.lock_depth == 0u);
    assert(fm_tracker_sloop_row(&adapter, 0));
    assert(fake.calls[0] == 1 && fake.phrase[0] == 2);
    assert(fake.calls[3] == 1 && fake.phrase[3] == 1);
    assert(fake.calls[1] == 0 && fake.calls[2] == 0);
    assert(fm_tracker_sloop_queue_quantized(&adapter, 0, 7, -2, 5,
                                            FM_TRACKER_BAR, 4, 4, 16));
    for (i = 1; i < 16; ++i) {
        assert(fm_tracker_sloop_row(&adapter, i));
        assert(fake.phrase[0] == 2);
    }
    assert(fm_tracker_sloop_row(&adapter, 16));
    assert(fake.phrase[0] == 7 && fake.transpose[0] == -2);
    assert(fake.calls[3] == 1); /* track 4 continues independently */
    assert(fm_tracker_sloop_stop_track(&adapter, 3, 17));
    assert(fm_tracker_sloop_row(&adapter, 17));
    assert(fake.calls[3] == 2 && fake.stopped[3]);
    assert(!fm_tracker_sloop_row(&adapter, 19)); /* discontinuities do not mutate SLOOP */
    assert(fake.calls[0] == 2 && fake.calls[3] == 2);
    fm_tracker_sloop_transport_reset(&adapter);
    assert(fake.calls[0] == 3 && fake.stopped[0]);
    assert(fake.calls[3] == 2 && fake.stopped[3]);
    assert(fm_tracker_sloop_start_chain(&adapter, 0, 0));
    assert(fm_tracker_sloop_row(&adapter, 0));
    assert(fake.calls[0] == 4 && fake.phrase[0] == 2);
    assert(fake.lock_depth == 0u);
    assert(sizeof(adapter) <= 700u);
    printf("tracker_sloop_adapter_test: ok (%u byte adapter)\n",
           (unsigned)sizeof adapter);
    return 0;
}
