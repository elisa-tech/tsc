#include <iostream>
#include "test-modules.child.h"

using namespace std;

Child::Child() : Base("Child") {}

void Child::do_init()
{
    cout << __PRETTY_FUNCTION__ << "\n";
}
void Child::do_work()
{
    cout << __PRETTY_FUNCTION__ << "\n";
}
void Child::do_final()
{
    cout << __PRETTY_FUNCTION__ << "\n";
}

int main()
{
    Child c;
    c.run();
    return 0;
}