#include "log.h"

struct ops1 {
    void (*callback)(void);
    int member;
};

struct ops2 {
    void (*callback)(void);
    int member;
};


void f5_cb_impl(void)
{
    log(__FUNCTION__);
}

struct ops1 ops = {
    .callback = f5_cb_impl
};


void f5_local_function(void){
    struct ops2 ops = {
        .callback = f5_cb_impl
    };
    log(__FUNCTION__);
    ops.callback();

}

void f5_main(void)
{
    ops.callback();
    f5_local_function();
}
