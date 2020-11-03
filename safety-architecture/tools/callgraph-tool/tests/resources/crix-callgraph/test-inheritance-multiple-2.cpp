#include <iostream>

using namespace std;

class Base_1
{
public:
    void base1_concrete() 
    { 
        cout << __PRETTY_FUNCTION__ << "\n"; 
    }
    virtual void base1_virtual()
    {
        cout << __PRETTY_FUNCTION__ << "\n"; 
    }
    virtual void base1_pure_virtual(int i) = 0;
};

class Base_2
{
public:
    virtual void base2_virtual()
    {
        cout << __PRETTY_FUNCTION__ << "\n"; 
    }
    virtual void base2_pure_virtual(int i) = 0;
};

class Child : public Base_1, public Base_2
{
public:
    void base1_virtual()
    {
        cout << __PRETTY_FUNCTION__ << "\n"; 
    }

    void base1_pure_virtual(int i) 
    {
        cout << __PRETTY_FUNCTION__ << "\n"; 
    }

    void base2_pure_virtual(int i) 
    {
        cout << __PRETTY_FUNCTION__ << "\n"; 
    }
};

int main()
{
    Base_1 *base1ptr;
    Base_2 *base2ptr;
    Child c;
    base1ptr = &c;

    base1ptr->base1_concrete();

    // Below two calls should be to the same target
    base1ptr->base1_virtual();
    c.base1_virtual();

    // Below two calls should be to the same target
    base1ptr->base1_pure_virtual(0);
    c.base1_pure_virtual(0);

    base2ptr = &c;
    // Child's
    base2ptr->base2_pure_virtual(0);
    // Base2's
    base2ptr->base2_virtual();

    return 0;
}