#include <iostream>

namespace FOO
{
    void say_hello()
    {
        std::cout << "Hello\n";
    }
}

int main()
{
    FOO::say_hello();
    return 0;
}