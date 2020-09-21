#include "log.h"

// inspired by arch/x86/kernel/apic/vector.c
struct obs_kernel_param {
	const char *str;
	int (*setup_func)(void);
	int early;
};

#define __setup_param(str, unique_id, fn, early)			\
	static const char __setup_str_##unique_id[] = str; 		\
	static struct obs_kernel_param __setup_##unique_id		\
		= { __setup_str_##unique_id, fn, early };           

#define __call(unique_id) \
    __setup_##unique_id.setup_func();

#define __setup(str, fn)						\
	__setup_param(str, fn, fn, 0)


static int show_lapic = 1; 

static int setup_show_lapic(void)
{
    log(__FUNCTION__);
    return 2;
}

__setup("show_lapic=", setup_show_lapic);

void f6_main(void)
{
    log(__FUNCTION__);
    show_lapic = __call(setup_show_lapic);
}
