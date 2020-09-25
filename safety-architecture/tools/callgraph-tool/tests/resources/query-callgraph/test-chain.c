#include <stdio.h>

typedef void (*fptr_t)();

void say_hello()
{
    printf("Hello\n");
}

void recursive_call(int i)
{
    say_hello();
    i = i - 1;
    if (i <= 0)
    {
        return;
    }
    else
    {
        recursive_call(i);
    }
}

void chain3()
{
    say_hello();
}

void chain2()
{
    chain3();
}

void chain1()
{
    chain2();
}

void start_of_longer_call_chain()
{
    chain1();
}

int main()
{
    say_hello();
    fptr_t fptr = say_hello;
    fptr();
    recursive_call(5);
    start_of_longer_call_chain();
}
