#include <iostream>

using namespace std;

namespace NS1 {
namespace NS2 {

class Base
{
public:
    void base_concrete() 
    { 
        cout << __PRETTY_FUNCTION__ << "\n"; 
    }
    virtual void base_virtual()
    {
        cout << __PRETTY_FUNCTION__ << "\n"; 
    }
    virtual void base_pure_virtual(int i) = 0;
};

class Child : public Base
{
public:
    void base_virtual()
    {
        cout << __PRETTY_FUNCTION__ << "\n"; 
    }

    void base_pure_virtual(int i) 
    {
        cout << __PRETTY_FUNCTION__ << "\n"; 
    }
};

void base_concrete()
{
    cout << __PRETTY_FUNCTION__ << "\n";
}

Child gchild;
Base *baseptr = &gchild;

}
}

int main()
{
    NS1::NS2::base_concrete();
    NS1::NS2::baseptr->base_concrete();

    // Below two calls should be to the same target function
    NS1::NS2::baseptr->base_virtual();
    NS1::NS2::gchild.base_virtual();

    // Below two calls should be to the same target function
    NS1::NS2::baseptr->base_pure_virtual(0);
    NS1::NS2::gchild.base_pure_virtual(0);

    return 0;
}