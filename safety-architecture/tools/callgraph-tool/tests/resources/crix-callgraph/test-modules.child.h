#ifndef TEST_MODULES_CHILD_H 
#define TEST_MODULES_CHILD_H 

#include "test-modules.base.h"

class Child : public Base
{
public:
    Child();
    void do_init();
    void do_work();
    void do_final();
};

#endif