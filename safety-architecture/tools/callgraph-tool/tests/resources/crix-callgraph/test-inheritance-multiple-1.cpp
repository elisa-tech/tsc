#include <iostream>

using namespace std;

class Base_1
{
public:
    void base1_concrete() 
    { 
        cout << __PRETTY_FUNCTION__ << "\n"; 
    }
};

class Base_2
{
public:
    void base2_concrete() 
    { 
        cout << __PRETTY_FUNCTION__ << "\n"; 
    }
};

class Child : public Base_1, public Base_2
{
};

int main()
{
    Child c;
    Base_1 *base1ptr = &c;
    Base_2 *base2ptr = &c;

    c.base1_concrete();
    base1ptr->base1_concrete();

    c.base2_concrete();
    base2ptr->base2_concrete();

    return 0;
}