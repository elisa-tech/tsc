#include "file2.h"
#include "log.h"

struct local_ops {
    void (*local_call)(void);
};

static void f2_local_function(void)
{
    log(__FUNCTION__);
}

static void f2_local_struct_par(struct local_ops* ops)
{
    log(__FUNCTION__);
    ops->local_call();
}

void f2_main(void){
    struct local_ops local = {
       .local_call = f2_local_function
    };
    log(__FUNCTION__);
    local.local_call();
    f2_local_struct_par(&local);
}
