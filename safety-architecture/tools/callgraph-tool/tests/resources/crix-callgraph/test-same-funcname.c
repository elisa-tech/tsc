#include <stdio.h>
#include "test-same-funcname.module.h"

static void say_hello()
{
    printf("Hello from test-same-funcname.c\n");
}

int main()
{
    say_hello();
    module_call();
}
