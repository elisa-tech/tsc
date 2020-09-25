#include "file3.h"
#include "log.h"


static const struct as_operations mem_aops;

int f3_check_equal(const struct as_operations* rhs)
{
    log(__FUNCTION__);
    if(rhs == &mem_aops)
        return 1;
    return 0;
}

static int f3_wp(struct page *page, void *wbc)
{
    log(__FUNCTION__);
    return 0;
}

static int f3_rp(struct file *file, struct page *page)
{
    log(__FUNCTION__);
    return 0;
}

static void f3_fp(struct page *page)
{
    log(__FUNCTION__);
}

void f3_main(void)
{
    log(__FUNCTION__);
    struct as_operations local = {
        .freepage = f3_fp
    };
    f3_check_equal(&local);
    f3_check_equal(&mem_aops);
}


static const struct as_operations mem_aops = {
    .writepage = f3_wp,
    .readpage = f3_rp
};
