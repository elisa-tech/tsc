#include "log.h"

#ifndef __cacheline_aligned
#define __cacheline_aligned __attribute__((__aligned__(64)))
#endif

struct metadata {
    int md1;
    int md2;
    float md3;
    double md4;
};

struct aligned_ops {
    int member1;
    struct metadata data __cacheline_aligned;
    char member2;
    void (*callback)(void);
} __cacheline_aligned;


static void f7_cb_implement(void)
{
    log(__FUNCTION__);
}

static const struct aligned_ops aops = {
    .callback = f7_cb_implement
};

void f7_main(void)
{
    log(__FUNCTION__);
    aops.callback();
}
