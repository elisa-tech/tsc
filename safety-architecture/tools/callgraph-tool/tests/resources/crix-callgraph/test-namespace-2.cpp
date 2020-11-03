#include <iostream>

namespace NS {
class Base {
public:
    virtual void base_pure_virtual() = 0;
};

class Child : public Base {
public:
    void base_pure_virtual() {
        std::cout << __PRETTY_FUNCTION__ << "\n";
    }
};
}


int main() {
    NS::Child child;
    NS::Base *baseptr = &child;
    baseptr->base_pure_virtual();
    return 0;
}