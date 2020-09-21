#include "file1.h"
#include "log.h"

// Function is called through m_ops structure member exec1
void m_ifunc1(void)
{
    log(__FUNCTION__);
}

// Function is called through m_ops structure member exec2
int m_ifunc2(void)
{
    log(__FUNCTION__);
    return 42;
}


static const struct m_ops m_exec = {
    .exec1 = m_ifunc1,
    .exec2 = m_ifunc2
};

static void f1_local(const struct m_ops* ops){
    log(__FUNCTION__);
    ops->exec1();
}

void f1_main(void)
{
    log(__FUNCTION__);
    f1_local(&m_exec);
    m_exec.exec2();
}
