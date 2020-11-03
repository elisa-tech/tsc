#include <iostream>

using namespace std;

class Base_1
{
public:
    virtual void foo() 
    { 
        cout << __PRETTY_FUNCTION__ << "\n"; 
    }
};

class Base_2
{
public:
    virtual void foo() 
    { 
        cout << __PRETTY_FUNCTION__ << "\n"; 
    }
};

class Child : public Base_1, public Base_2
{
public:
    void foo()
    {
        Base_1::foo();
        Base_2::foo();
        cout << __PRETTY_FUNCTION__ << "\n"; 
    }
};

int main()
{
    Child c;
    c.foo();
    return 0;
}
