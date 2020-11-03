#include <iostream>

using namespace std;

class Base_1
{
public:
    void base1_concrete() 
    { 
        cout << __PRETTY_FUNCTION__ << "\n"; 
    }
    virtual void base1_pure_virtual(int i) = 0;
};

class Child_1 : public Base_1
{
public:
    void child1_concrete() 
    { 
        cout << __PRETTY_FUNCTION__ << "\n"; 
    }
    void base1_pure_virtual(int i) 
    {
        cout << __PRETTY_FUNCTION__ << "\n"; 
    }
};

class Child_2 : public Child_1 
{
public:
    void base1_pure_virtual(int i) 
    {
        cout << __PRETTY_FUNCTION__ << "\n"; 
    }
};

int main()
{
    Child_2 c;
    c.base1_concrete();
    c.child1_concrete();
    c.base1_pure_virtual(0);
    return 0;
}