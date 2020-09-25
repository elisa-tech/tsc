#include <stdio.h>

static void say_hello()
{
    printf("Hello from module.c\n");
}

void module_call()
{
    say_hello();
}