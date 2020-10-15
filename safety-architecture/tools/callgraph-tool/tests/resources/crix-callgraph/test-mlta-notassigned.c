#include <stdio.h>

void say_hello()
{
    printf("Hello\n");
}

struct S {
    void (*function_pointer)(void);
};

int main(void)
{
    void (*unrelated_fptr)(void);
    unrelated_fptr = say_hello;
    struct S s;
    // 'unrelated_fptr' should not be a potential call target for
    // s.function pointer because it was never assigned to it.
    s.function_pointer();
    return 0;
}
