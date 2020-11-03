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

Child child;
Base *baseptr = &child;
}

int main() {
    NS::baseptr->base_pure_virtual();
    return 0;
}