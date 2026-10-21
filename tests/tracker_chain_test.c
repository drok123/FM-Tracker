#include "../firmware/tracker_chain.h"
#include <assert.h>
#include <stdio.h>

int main(void)
{
    fm_tracker_t tracker;
    fm_tracker_change_t changes[FM_TRACKER_TRACKS];
    uint32_t scheduled;
    const fm_tracker_entry_t a[] = {{10, 2, 2, 0}, {11, 3, 1, 5}};
    const fm_tracker_entry_t b[] = {{20, 3, 1, 0}, {21, 1, 2, -2}};
    fm_tracker_init(&tracker);
    assert(fm_tracker_set_chain(&tracker, 0, a, 2, 1));
    assert(fm_tracker_set_chain(&tracker, 1, b, 2, 1));
    assert(fm_tracker_set_chain(&tracker, 2, NULL, 0, 0));
    assert(!fm_tracker_set_chain(&tracker, 4, NULL, 0, 0));
    assert(!fm_tracker_set_chain(&tracker, 2, a, 17, 0));
    assert(fm_tracker_quantize_row(17, FM_TRACKER_BAR, 4, 4, 16, &scheduled));
    assert(scheduled == 32);
    assert(fm_tracker_quantize_row(5, FM_TRACKER_BEAT, 4, 4, 16, &scheduled));
    assert(scheduled == 8);
    assert(!fm_tracker_quantize_row(UINT32_MAX, FM_TRACKER_BAR, 4, 4, 16, &scheduled));
    assert(fm_tracker_start_chain(&tracker, 0, 0));
    assert(fm_tracker_start_chain(&tracker, 1, 0));
    assert(!fm_tracker_start_chain(&tracker, 2, 0));
    assert(fm_tracker_advance(&tracker, 0, changes));
    assert(changes[0].changed && changes[0].phrase == 10);
    assert(changes[1].changed && changes[1].phrase == 20);
    assert(fm_tracker_advance(&tracker, 2, changes) == 0);
    assert(fm_tracker_advance(&tracker, 1, changes));
    assert(!changes[0].changed && !changes[1].changed);
    assert(fm_tracker_advance(&tracker, 2, changes));
    assert(changes[0].changed && changes[0].phrase == 10);
    assert(!changes[1].changed);
    assert(fm_tracker_advance(&tracker, 3, changes));
    assert(changes[1].changed && changes[1].phrase == 21);
    assert(fm_tracker_queue_quantized(&tracker, 1, 30, 7, 5,
                                      FM_TRACKER_BAR, 4, 4, 16));
    assert(fm_tracker_queue_quantized(&tracker, 1, 31, -4, 5,
                                      FM_TRACKER_BAR, 4, 4, 16));
    assert(fm_tracker_advance(&tracker, 4, changes));
    assert(changes[1].changed && changes[1].phrase == 21);
    assert(fm_tracker_advance(&tracker, 5, changes));
    assert(changes[1].changed && changes[1].phrase == 20);
    for (uint32_t row = 6; row < 16; ++row)
        assert(fm_tracker_advance(&tracker, row, changes));
    assert(fm_tracker_advance(&tracker, 16, changes));
    assert(changes[1].changed && changes[1].phrase == 31 && changes[1].transpose == -4);
    assert(fm_tracker_stop_track(&tracker, 1, 17));
    assert(fm_tracker_advance(&tracker, 17, changes));
    assert(changes[1].changed && changes[1].stopped);
    assert(fm_tracker_start_chain(&tracker, 1, 18));
    assert(fm_tracker_advance(&tracker, 18, changes));
    assert(changes[1].changed && changes[1].phrase == 20);
    assert(fm_tracker_advance(&tracker, 19, changes));
    assert(!changes[1].changed);
    assert(fm_tracker_advance(&tracker, 20, changes));
    assert(fm_tracker_advance(&tracker, 21, changes));
    assert(changes[1].changed && changes[1].phrase == 21);
    assert(fm_tracker_set_chain(&tracker, 2, b, 2, 0));
    assert(fm_tracker_start_chain(&tracker, 2, 22));
    assert(fm_tracker_advance(&tracker, 22, changes));
    assert(changes[2].changed && changes[2].phrase == 20);
    assert(fm_tracker_advance(&tracker, 23, changes));
    assert(fm_tracker_advance(&tracker, 24, changes));
    assert(fm_tracker_advance(&tracker, 25, changes));
    assert(changes[2].changed && changes[2].phrase == 21);
    assert(fm_tracker_advance(&tracker, 26, changes));
    assert(changes[2].changed && changes[2].phrase == 21);
    assert(fm_tracker_advance(&tracker, 27, changes));
    assert(changes[2].changed && changes[2].stopped);
    assert(sizeof(fm_tracker_t) <= 640u);
    printf("tracker_chain_test: ok (%u byte state)\n", (unsigned)sizeof(tracker));
    return 0;
}
