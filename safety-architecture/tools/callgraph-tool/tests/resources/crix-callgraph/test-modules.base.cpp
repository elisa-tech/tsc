#include <iostream>
#include "test-modules.base.h"

using namespace std;

void Base::run()
{
    cout << __PRETTY_FUNCTION__ << "\n";
    // These calls can be to the Base's implementation,
    // or to the (any) Child's implementation depending on the
    // object through which the call to Base::run() was invoked.
    this->do_init();
    this->do_work();
    this->do_final();
}
