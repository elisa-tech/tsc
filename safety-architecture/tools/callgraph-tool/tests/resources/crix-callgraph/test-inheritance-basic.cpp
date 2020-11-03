#include <iostream>

using namespace std;

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

int main()
{
    Base *baseptr;
    Child c;
    baseptr = &c;

    base_concrete();
    baseptr->base_concrete();

    // Below two calls should be to the same target function
    baseptr->base_virtual();
    c.base_virtual();

    // Below two calls should be to the same target function
    baseptr->base_pure_virtual(0);
    c.base_pure_virtual(0);

    return 0;
}